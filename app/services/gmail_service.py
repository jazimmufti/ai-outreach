"""Gmail OAuth 2.0 service and real email sending via Gmail API with PKCE protection."""

import os
import json
import time
import secrets
import threading
import base64
import hashlib
import logging
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import httpx
from cryptography.fernet import Fernet, InvalidToken

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)

# Minimal necessary scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# Persistent OAuth transaction store for ongoing OAuth transactions (survives uvicorn reloads and separate HTTP requests)
_oauth_transaction_store: Dict[str, Dict[str, Any]] = {}
_consumed_oauth_states: set = set()
_store_lock = threading.RLock()
OAUTH_SESSION_TTL_SECONDS = 900  # 15 minutes TTL
OAUTH_SESSION_FILE = str(settings.BASE_DIR / ".oauth_sessions.json") if hasattr(settings, "BASE_DIR") else os.path.join(os.path.dirname(settings.TOKEN_FILE), ".oauth_sessions.json")


def _get_state_fernet() -> Fernet:
    """Derive a Fernet cipher instance from SESSION_SECRET_KEY for stateless tamper-proof OAuth state."""
    secret = (settings.SESSION_SECRET_KEY or "default_outreach_secret_key_84920").encode("utf-8")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(derived_key)


def encode_signed_oauth_state(code_verifier: str) -> str:
    """Create a cryptographically signed, encrypted, URL-safe state parameter carrying PKCE verifier."""
    fernet = _get_state_fernet()
    payload = {
        "v": code_verifier,
        "n": secrets.token_urlsafe(16),
        "t": time.time()
    }
    raw_json = json.dumps(payload)
    return fernet.encrypt(raw_json.encode("utf-8")).decode("utf-8")


def decode_signed_oauth_state(state: str) -> Optional[str]:
    """Verify cryptographic signature, TTL, and replay status of an OAuth state, returning PKCE verifier."""
    if not state or not isinstance(state, str):
        return None

    with _store_lock:
        if state in _consumed_oauth_states:
            logger.warning(f"OAuth state has already been consumed (replay prevention).")
            return None

    fernet = _get_state_fernet()
    try:
        decrypted_bytes = fernet.decrypt(state.encode("utf-8"))
        payload = json.loads(decrypted_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        created_at = payload.get("t", 0)
        now = time.time()
        if now - created_at > OAUTH_SESSION_TTL_SECONDS or created_at > now + 60:
            logger.warning(f"OAuth signed state expired: created_at={created_at}, now={now}")
            return None

        code_verifier = payload.get("v")
        if code_verifier and isinstance(code_verifier, str):
            return code_verifier
    except InvalidToken:
        logger.debug("State is not a valid Fernet token or was tampered with.")
    except Exception as e:
        logger.warning(f"Error decoding OAuth signed state: {e}")

    return None


def _load_oauth_sessions() -> None:
    """Load persisted OAuth sessions from disk and merge non-destructively into memory."""
    global _oauth_transaction_store
    if not os.path.exists(OAUTH_SESSION_FILE):
        return
    try:
        with open(OAUTH_SESSION_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        if isinstance(disk_data, dict):
            now = time.time()
            for k, v in disk_data.items():
                if isinstance(v, dict) and k not in _oauth_transaction_store:
                    if now - v.get("created_at", 0) <= OAUTH_SESSION_TTL_SECONDS:
                        _oauth_transaction_store[k] = v
    except Exception as e:
        logger.debug(f"Could not load OAuth sessions from disk: {e}")


def _save_oauth_sessions() -> None:
    """Save active in-memory OAuth sessions to disk."""
    try:
        dir_name = os.path.dirname(os.path.abspath(OAUTH_SESSION_FILE))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(OAUTH_SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(_oauth_transaction_store, f)
    except Exception as e:
        logger.debug(f"Could not save OAuth sessions to disk: {e}")


def _cleanup_expired_sessions() -> None:
    """Clean up expired OAuth states to prevent memory leaks."""
    now = time.time()
    with _store_lock:
        _load_oauth_sessions()
        expired_keys = [
            k for k, v in _oauth_transaction_store.items()
            if now - v.get("created_at", 0) > OAUTH_SESSION_TTL_SECONDS
        ]
        for k in expired_keys:
            _oauth_transaction_store.pop(k, None)
        if expired_keys:
            _save_oauth_sessions()


def store_oauth_session(state: str, code_verifier: str) -> None:
    """Store the PKCE code_verifier associated with an OAuth state."""
    if not state or not code_verifier:
        return
    with _store_lock:
        _cleanup_expired_sessions()
        _oauth_transaction_store[state] = {
            "code_verifier": code_verifier,
            "created_at": time.time()
        }
        _save_oauth_sessions()


def get_oauth_code_verifier(state: str) -> Optional[str]:
    """Retrieve the PKCE code_verifier for a given OAuth state if still valid."""
    if not state or not isinstance(state, str):
        return None

    # 1. First check in-memory store
    with _store_lock:
        _cleanup_expired_sessions()
        entry = _oauth_transaction_store.get(state)
        if entry:
            if time.time() - entry.get("created_at", 0) <= OAUTH_SESSION_TTL_SECONDS:
                return entry.get("code_verifier")
            else:
                _oauth_transaction_store.pop(state, None)
                _save_oauth_sessions()

    # 2. Cryptographic state token decoding (survives worker switch, server restart, multi-replica)
    signed_verifier = decode_signed_oauth_state(state)
    if signed_verifier:
        return signed_verifier

    # 3. Disk file fallback
    with _store_lock:
        _load_oauth_sessions()
        entry = _oauth_transaction_store.get(state)
        if entry:
            if time.time() - entry.get("created_at", 0) <= OAUTH_SESSION_TTL_SECONDS:
                return entry.get("code_verifier")

    return None


def remove_oauth_session(state: str) -> None:
    """Remove an OAuth session once the token exchange has completed and mark consumed."""
    if not state:
        return
    with _store_lock:
        _oauth_transaction_store.pop(state, None)
        _consumed_oauth_states.add(state)
        _save_oauth_sessions()




# Thread-safe in-memory cache for the authenticated email address
_cached_user_email: Optional[str] = None

def get_stored_credentials() -> Optional[Credentials]:
    """Retrieve and refresh stored OAuth credentials from GMAIL_TOKEN_JSON env var or token file."""
    global _cached_user_email

    # 1. First check if GMAIL_TOKEN_JSON environment variable is configured
    if settings.GMAIL_TOKEN_JSON and settings.GMAIL_TOKEN_JSON.strip():
        try:
            token_info = json.loads(settings.GMAIL_TOKEN_JSON.strip())
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds if creds and creds.valid else None
        except Exception as e:
            logger.warning(f"Error loading credentials from GMAIL_TOKEN_JSON: {e}")

    # 2. Check token file on disk
    token_path = settings.TOKEN_FILE
    if not os.path.exists(token_path):
        _cached_user_email = None
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            try:
                with open(token_path, "w") as token_file:
                    token_file.write(creds.to_json())
            except Exception:
                pass
        return creds if creds and creds.valid else None
    except Exception as e:
        logger.error(f"Error loading stored credentials: {e}")
        return None



def fetch_user_email_from_token(creds: Credentials) -> Optional[str]:
    """Retrieve user email address from Google OAuth2 UserInfo API using openid scope with caching."""
    global _cached_user_email
    if _cached_user_email:
        return _cached_user_email

    try:
        # 1. Try id_token if present
        if hasattr(creds, "id_token") and creds.id_token and isinstance(creds.id_token, dict):
            if "email" in creds.id_token:
                _cached_user_email = creds.id_token["email"]
                return _cached_user_email

        # 2. Fetch from Google UserInfo endpoint using bearer token
        if creds.token:
            res = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {creds.token}"},
                timeout=4.0
            )
            if res.status_code == 200:
                data = res.json()
                _cached_user_email = data.get("email")
                return _cached_user_email
            elif res.status_code == 401 and creds.refresh_token:
                # Token may have expired between checks, attempt fresh refresh
                creds.refresh(Request())
                with open(settings.TOKEN_FILE, "w") as token_file:
                    token_file.write(creds.to_json())
                res2 = httpx.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {creds.token}"},
                    timeout=4.0
                )
                if res2.status_code == 200:
                    _cached_user_email = res2.json().get("email")
                    return _cached_user_email
    except Exception as e:
        logger.warning(f"Could not fetch email from UserInfo: {e}")
    return None


def get_gmail_status() -> Dict[str, Any]:
    """Check if a Gmail account is currently authenticated and retrieve sender email instantly."""
    global _cached_user_email
    creds = get_stored_credentials()
    if not creds:
        _cached_user_email = None
        return {"connected": False, "email": None}

    # Fetch email via cache or UserInfo endpoint
    sender_email = _cached_user_email or fetch_user_email_from_token(creds)
    if not sender_email:
        sender_email = "Connected Account"

    return {
        "connected": True,
        "email": sender_email,
        "scopes": creds.scopes
    }


def generate_oauth_url(custom_state: Optional[str] = None) -> Tuple[str, str, str]:
    """Generate the Google OAuth2 authorization URL with PKCE and cryptographically signed state.
    
    Returns:
        Tuple of (auth_url, state, code_verifier)
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured in .env to connect Gmail."
        )

    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }

    # Generate high-entropy PKCE code verifier (64 bytes URL-safe)
    code_verifier = secrets.token_urlsafe(64)

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=False
    )
    flow.code_verifier = code_verifier

    # Create signed & encrypted state carrying code_verifier or custom state
    if custom_state:
        state = custom_state
    else:
        state = encode_signed_oauth_state(code_verifier)

    auth_url, auth_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )

    # Persist in memory store as well
    store_oauth_session(auth_state, code_verifier)

    return auth_url, auth_state, code_verifier


def exchange_code_for_tokens(
    code: str, 
    state: Optional[str] = None, 
    code_verifier: Optional[str] = None
) -> Dict[str, Any]:
    """Exchange authorization code for OAuth tokens using the original PKCE code_verifier."""
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }

    # If code_verifier was not supplied explicitly, retrieve from store / signed state using state
    if not code_verifier and state:
        code_verifier = get_oauth_code_verifier(state)

    if not code_verifier:
        raise ValueError(
            "Missing PKCE code verifier or OAuth session expired. Please restart the Gmail connection flow."
        )

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
        autogenerate_code_verifier=False
    )
    flow.code_verifier = code_verifier

    # Pass the original PKCE code_verifier into fetch_token
    flow.fetch_token(code=code, code_verifier=code_verifier)
    credentials = flow.credentials

    # Save credentials securely to token file
    try:
        with open(settings.TOKEN_FILE, "w") as token_file:
            token_file.write(credentials.to_json())
    except Exception as e:
        logger.warning(f"Could not write token.json to disk: {e}")

    # Clean up one-time OAuth state
    if state:
        remove_oauth_session(state)

    # Invalidate email cache
    global _cached_user_email
    _cached_user_email = None

    # Get sender profile email
    status = get_gmail_status()
    return status



def disconnect_gmail() -> bool:
    """Disconnect Gmail integration by removing stored credentials."""
    global _cached_user_email
    _cached_user_email = None
    if os.path.exists(settings.TOKEN_FILE):
        try:
            os.remove(settings.TOKEN_FILE)
            return True
        except Exception as e:
            logger.error(f"Error removing token file: {e}")
            return False
    return True


from email.mime.multipart import MIMEMultipart


def send_test_email(
    recipient: str, 
    subject: str, 
    body: str, 
    confirm_url: Optional[str] = None, 
    reject_url: Optional[str] = None
) -> Dict[str, Any]:
    """Send an actual email via Gmail API using the connected user account with HTML Yes/No confirmation buttons."""
    creds = get_stored_credentials()
    if not creds:
        raise ValueError("Gmail account is not connected. Please connect your Gmail account via OAuth first.")

    try:
        # Get sender email from userinfo
        status = get_gmail_status()
        sender_email = status.get("email") or "me"

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        # Build Plain Text Body
        plain_body = body
        if confirm_url and reject_url:
            plain_body += (
                f"\n\n--------------------------------------------------\n"
                f"CONFIRM OR REJECT COLLABORATION:\n\n"
                f"[Yes, I confirm this collaboration]:\n{confirm_url}\n\n"
                f"[No, I do not confirm]:\n{reject_url}\n"
                f"--------------------------------------------------"
            )

        # Build HTML Body with styled Yes/No buttons
        html_buttons = ""
        if confirm_url and reject_url:
            html_buttons = f"""
            <div style="margin: 24px 0; padding: 20px; background: #FAF7F0; border: 2px solid #111827; border-radius: 4px; text-align: center;">
                <p style="margin: 0 0 16px 0; font-family: sans-serif; font-size: 14.5px; font-weight: bold; color: #111827;">Can you confirm this collaboration?</p>
                <div style="display: block; margin-top: 12px;">
                    <a href="{confirm_url}" style="display: inline-block; background: #00D26A; color: #000000; text-decoration: none; font-family: sans-serif; font-size: 14px; font-weight: bold; padding: 12px 24px; border: 2px solid #111827; border-radius: 2px; margin: 4px 6px;">
                        ✓ Yes, I confirm this collaboration
                    </a>
                    &nbsp;
                    <a href="{reject_url}" style="display: inline-block; background: #FFFFFF; color: #111827; text-decoration: none; font-family: sans-serif; font-size: 14px; font-weight: bold; padding: 12px 20px; border: 2px solid #111827; border-radius: 2px; margin: 4px 6px;">
                        ✕ No, I do not confirm
                    </a>
                </div>
            </div>
            """

        formatted_html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #FAF7F0; color: #111827; padding: 24px 12px; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; border: 2px solid #111827; border-radius: 4px; padding: 32px 28px;">
        <div style="margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1.5px solid #E5E7EB;">
            <strong style="font-size: 20px; letter-spacing: -0.02em; color: #111827;">Arclent</strong>
        </div>
        <p style="font-size: 15px; line-height: 1.6; color: #111827; margin: 0 0 16px 0; white-space: pre-wrap;">{body}</p>
        {html_buttons}
        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #6B7280; font-family: monospace;">
            Sent securely via Arclent • Creator Collaboration & Credentials Verification
        </div>
    </div>
</body>
</html>"""

        message = MIMEMultipart("alternative")
        message["to"] = recipient
        message["from"] = sender_email
        message["subject"] = subject

        part_plain = MIMEText(plain_body, "plain", "utf-8")
        part_html = MIMEText(formatted_html_body, "html", "utf-8")

        message.attach(part_plain)
        message.attach(part_html)

        # Base64url encode the raw message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        send_result = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        message_id = send_result.get("id")

        return {
            "success": True,
            "message": "Verification email sent successfully via Gmail API",
            "recipient": recipient,
            "sender": sender_email,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send email via Gmail API: {e}", exc_info=True)
        raise RuntimeError(f"Gmail sending failed: {str(e)}")
