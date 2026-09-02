"""Gmail OAuth 2.0 service and real email sending via Gmail API with PKCE protection."""

import os
import time
import secrets
import threading
import base64
import logging
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import httpx

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

# Thread-safe in-memory store for ongoing OAuth transactions (state -> {code_verifier, created_at})
_oauth_transaction_store: Dict[str, Dict[str, Any]] = {}
_store_lock = threading.Lock()
OAUTH_SESSION_TTL_SECONDS = 900  # 15 minutes TTL


def _cleanup_expired_sessions() -> None:
    """Clean up expired OAuth states to prevent memory leaks."""
    now = time.time()
    with _store_lock:
        expired_keys = [
            k for k, v in _oauth_transaction_store.items()
            if now - v.get("created_at", 0) > OAUTH_SESSION_TTL_SECONDS
        ]
        for k in expired_keys:
            _oauth_transaction_store.pop(k, None)


def store_oauth_session(state: str, code_verifier: str) -> None:
    """Store the PKCE code_verifier associated with an OAuth state."""
    _cleanup_expired_sessions()
    with _store_lock:
        _oauth_transaction_store[state] = {
            "code_verifier": code_verifier,
            "created_at": time.time()
        }


def get_oauth_code_verifier(state: str) -> Optional[str]:
    """Retrieve the PKCE code_verifier for a given OAuth state if still valid."""
    _cleanup_expired_sessions()
    with _store_lock:
        entry = _oauth_transaction_store.get(state)
        if entry:
            if time.time() - entry.get("created_at", 0) <= OAUTH_SESSION_TTL_SECONDS:
                return entry.get("code_verifier")
    return None


def remove_oauth_session(state: str) -> None:
    """Remove an OAuth session once the token exchange has completed."""
    with _store_lock:
        _oauth_transaction_store.pop(state, None)


# Thread-safe in-memory cache for the authenticated email address
_cached_user_email: Optional[str] = None

def get_stored_credentials() -> Optional[Credentials]:
    """Retrieve and refresh stored OAuth credentials from token file."""
    global _cached_user_email
    token_path = settings.TOKEN_FILE
    if not os.path.exists(token_path):
        _cached_user_email = None
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
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
    """Generate the Google OAuth2 authorization URL with PKCE and cryptographically random state.
    
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

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    # Use cryptographically random 32-byte URL-safe state
    state = custom_state or secrets.token_urlsafe(32)

    auth_url, auth_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )

    code_verifier = flow.code_verifier
    if not code_verifier:
        raise RuntimeError("Failed to generate PKCE code_verifier in OAuth flow.")

    # Persist the code_verifier associated with this state
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

    # If code_verifier was not supplied explicitly, retrieve from store using state
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
        state=state
    )

    # Pass the original PKCE code_verifier into fetch_token
    flow.fetch_token(code=code, code_verifier=code_verifier)
    credentials = flow.credentials

    # Save credentials securely to token file
    with open(settings.TOKEN_FILE, "w") as token_file:
        token_file.write(credentials.to_json())

    # Clean up one-time OAuth state
    if state:
        remove_oauth_session(state)

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


def send_test_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an actual email via Gmail API using the connected user account."""
    creds = get_stored_credentials()
    if not creds:
        raise ValueError("Gmail account is not connected. Please connect your Gmail account via OAuth first.")

    try:
        # Get sender email from userinfo
        status = get_gmail_status()
        sender_email = status.get("email") or "me"

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        # Create MIME email message
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = recipient
        message["from"] = sender_email
        message["subject"] = subject

        # Base64url encode the raw message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        send_result = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        message_id = send_result.get("id")

        return {
            "success": True,
            "message": "Test email sent successfully via Gmail API",
            "recipient": recipient,
            "sender": sender_email,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send email via Gmail API: {e}", exc_info=True)
        raise RuntimeError(f"Gmail sending failed: {str(e)}")
