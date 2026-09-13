"""Discord OAuth2 and Server Membership Auto-Verification API routes."""

import time
import secrets
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse

from app.config import settings
from app.models.schemas import (
    OutreachStage,
    DiscordVerificationStatusResponse,
    SetDiscordUserIdRequest
)
from app.services.session_manager import get_session, save_session
from app.services import discord_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discord-verification"])

# Thread-safe in-memory store for OAuth state -> session tracking
_oauth_states: Dict[str, Dict[str, Any]] = {}
_oauth_lock = threading.Lock()
OAUTH_STATE_TTL_SECONDS = 900  # 15 minutes


def _clean_expired_states() -> None:
    """Evict expired OAuth state entries."""
    now = time.time()
    with _oauth_lock:
        expired = [s for s, data in _oauth_states.items() if now - data.get("created_at", 0) > OAUTH_STATE_TTL_SECONDS]
        for s in expired:
            _oauth_states.pop(s, None)


def store_oauth_state(state: str, session_id: str, return_to: Optional[str] = None) -> None:
    """Store CSRF state tied to an outreach session."""
    _clean_expired_states()
    with _oauth_lock:
        _oauth_states[state] = {
            "session_id": session_id,
            "return_to": return_to,
            "created_at": time.time()
        }


def consume_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """Validate and consume a one-time OAuth CSRF state."""
    _clean_expired_states()
    with _oauth_lock:
        data = _oauth_states.pop(state, None)
        if data:
            if time.time() - data.get("created_at", 0) <= OAUTH_STATE_TTL_SECONDS:
                return data
    return None


def _find_discord_invite_url(session) -> Optional[str]:
    """Helper to retrieve detected Discord invite URL from session."""
    if session.discord_invite_url:
        return session.discord_invite_url
    if session.discord_profile and session.discord_profile.discord_invite:
        return session.discord_profile.discord_invite
    if session.social_profiles:
        for s in session.social_profiles:
            if (s.platform or "").lower() == "discord":
                if s.discord_invite:
                    return s.discord_invite
                if s.url and ("discord.gg" in s.url or "discord.com/invite" in s.url):
                    return s.url
    return None


# ------------------------------------------------------------------------------
# 1. Initiate Discord OAuth Verification Flow
# ------------------------------------------------------------------------------

@router.get("/discord/verify")
@router.get("/api/discord/verify")
async def discord_verify_endpoint(
    request: Request,
    session_id: str = Query(..., description="Outreach session ID"),
    return_to: Optional[str] = Query(None, description="Optional return URL after verification"),
    as_json: Optional[bool] = Query(False, alias="json", description="Return JSON instead of redirect")
):
    """Initiate Discord OAuth2 authorization for server membership auto-verification.
    
    Minimum scope: 'identify' to securely retrieve creator's Discord User ID snowflake.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session not found or expired.")

    # Check if already verified
    if session.discord_verification_status == "verified":
        if as_json or "application/json" in request.headers.get("accept", ""):
            return {
                "verified": True,
                "status": "verified",
                "message": "Discord server membership already verified.",
                "discord_user_id": session.discord_user_id,
                "discord_guild_id": session.discord_guild_id,
                "discord_verified_at": session.discord_verified_at
            }
        # If already verified and direct navigation, return success view
        return _render_html_result(
            title="Discord Membership Verified ✓",
            status_code_name="verified",
            message="You are a member of this Discord server.",
            is_success=True,
            guild_name=session.discord_guild_name or "Discord Server",
            user_id=session.discord_user_id,
            invite_url=session.discord_invite_url,
            session_id=session_id
        )

    # Generate secure state
    state = secrets.token_urlsafe(32)
    store_oauth_state(state, session_id, return_to)

    try:
        request.session["discord_oauth_state"] = state
    except Exception:
        pass

    try:
        auth_url = discord_service.generate_discord_oauth_url(state)
    except discord_service.DiscordConfigurationError as dce:
        logger.error(f"Discord OAuth configuration error: {dce.message}")
        raise HTTPException(status_code=500, detail=dce.message)

    if as_json or "application/json" in request.headers.get("accept", ""):
        return {
            "auth_url": auth_url,
            "state": state,
            "session_id": session_id
        }

    return RedirectResponse(auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# ------------------------------------------------------------------------------
# 2. Discord OAuth2 Callback Endpoint
# ------------------------------------------------------------------------------

@router.get("/discord/callback", response_class=HTMLResponse)
@router.get("/api/discord/callback", response_class=HTMLResponse)
async def discord_callback_endpoint(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None)
):
    """Handle Discord OAuth2 redirect callback, retrieve Discord User ID, and verify server membership.
    
    Verification Flow:
    1. Validate OAuth state (CSRF protection)
    2. Handle OAuth cancel/denial
    3. Exchange code for access token (POST /oauth2/token)
    4. Fetch user profile (GET /users/@me) -> extract Discord User ID snowflake
    5. Resolve detected invite URL to target Discord Guild/Server ID (GET /invites/{code})
    6. Check membership with Arclent Bot (GET /guilds/{guild_id}/members/{user_id})
    7. Update session to 'verified', 'not_verified', or 'server_not_resolved'
    8. Return safe, responsive status page
    """
    logger.info(f"[Discord Callback] code_present={bool(code)}, state_present={bool(state)}, error={error}")

    # Handle user cancellation / denial
    if error:
        logger.warning(f"[Discord Callback] OAuth cancelled or denied: {error} - {error_description}")
        session_id = None
        if state:
            state_data = consume_oauth_state(state)
            if state_data:
                session_id = state_data.get("session_id")
                session = get_session(session_id)
                if session:
                    session.discord_verification_status = "oauth_failed"
                    save_session(session)

        return _render_html_result(
            title="✕ Discord Verification Cancelled",
            status_code_name="oauth_failed",
            message="Discord authorization was cancelled or denied. Please try again when ready.",
            is_success=False,
            session_id=session_id
        )

    # Validate state
    if not state:
        logger.warning("[Discord Callback] Missing state parameter.")
        return _render_html_result(
            title="✕ Invalid Request",
            status_code_name="oauth_failed",
            message="Invalid or missing OAuth state parameter.",
            is_success=False
        )

    state_data = consume_oauth_state(state)
    if not state_data:
        logger.warning(f"[Discord Callback] Invalid or expired state '{state}'.")
        return _render_html_result(
            title="✕ Session Expired",
            status_code_name="oauth_failed",
            message="Your verification session has expired. Please return to the app and click 'Verify Discord' again.",
            is_success=False
        )

    session_id = state_data["session_id"]
    session = get_session(session_id)
    if not session:
        logger.warning(f"[Discord Callback] Session {session_id} not found.")
        return _render_html_result(
            title="✕ Session Not Found",
            status_code_name="verification_error",
            message="Your outreach session was not found or has expired.",
            is_success=False
        )

    if not code:
        logger.warning("[Discord Callback] Missing authorization code.")
        session.discord_verification_status = "oauth_failed"
        save_session(session)
        return _render_html_result(
            title="✕ Verification Failed",
            status_code_name="oauth_failed",
            message="Discord did not return an authorization code.",
            is_success=False,
            session_id=session_id
        )

    # Step 3: Exchange code for tokens
    try:
        token_data = await discord_service.exchange_oauth_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise discord_service.DiscordOAuthError("Discord OAuth did not return an access token.")
    except discord_service.DiscordRateLimitError:
        session.discord_verification_status = "verification_error"
        save_session(session)
        return _render_html_result(
            title="✕ Discord Rate Limit",
            status_code_name="verification_error",
            message="Discord rate limit reached. Please wait a minute and retry verification.",
            is_success=False,
            session_id=session_id
        )
    except discord_service.DiscordServiceError as dse:
        logger.error(f"[Discord Callback] Token exchange failed: {dse.message}")
        session.discord_verification_status = "oauth_failed"
        save_session(session)
        return _render_html_result(
            title="✕ Discord Authorization Failed",
            status_code_name="oauth_failed",
            message="Could not complete Discord authorization. Please retry.",
            is_success=False,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"[Discord Callback] Unexpected token exchange error: {e}", exc_info=True)
        session.discord_verification_status = "oauth_failed"
        save_session(session)
        return _render_html_result(
            title="✕ OAuth Error",
            status_code_name="oauth_failed",
            message="An unexpected error occurred during Discord authentication.",
            is_success=False,
            session_id=session_id
        )

    # Step 4: Obtain authenticated Discord user (identifying by user_id snowflake)
    try:
        user_info = await discord_service.get_authenticated_user(access_token)
        discord_user_id = user_info["id"]
        logger.info(f"[Discord Callback] Authenticated user_id={discord_user_id}, username={user_info.get('username')}")
    except Exception as e:
        logger.error(f"[Discord Callback] Failed to fetch authenticated user: {e}", exc_info=True)
        session.discord_verification_status = "oauth_failed"
        save_session(session)
        return _render_html_result(
            title="✕ Failed to Identify User",
            status_code_name="oauth_failed",
            message="Could not retrieve your Discord User ID. Please try logging in again.",
            is_success=False,
            session_id=session_id
        )

    # Step 5: Locate detected Discord invite URL
    detected_invite = _find_discord_invite_url(session)
    if not detected_invite:
        logger.warning(f"[Discord Callback] No Discord invite URL found on session {session_id}")
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "server_not_resolved"
        save_session(session)
        return _render_html_result(
            title="✕ Server Not Resolved",
            status_code_name="server_not_resolved",
            message="No Discord server or invite link was detected in this creator's description.",
            is_success=False,
            user_id=discord_user_id,
            session_id=session_id
        )

    # Step 6: Resolve invite to guild ID using official Discord API
    try:
        guild_info = await discord_service.resolve_invite_to_guild(detected_invite)
        guild_id = guild_info["guild_id"]
        guild_name = guild_info["guild_name"]
        invite_url = guild_info.get("invite_url") or detected_invite
        session.discord_guild_id = guild_id
        session.discord_guild_name = guild_name
        session.discord_invite_url = invite_url
    except discord_service.DiscordInviteResolutionError as dire:
        logger.warning(f"[Discord Callback] Invite resolution error for '{detected_invite}': {dire.message}")
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "server_not_resolved"
        save_session(session)
        return _render_html_result(
            title="✕ Server Not Resolved",
            status_code_name="server_not_resolved",
            message="The detected Discord invite link is expired, deleted, or invalid and could not be resolved to a server.",
            is_success=False,
            user_id=discord_user_id,
            invite_url=detected_invite,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"[Discord Callback] Error resolving invite '{detected_invite}': {e}", exc_info=True)
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "server_not_resolved"
        save_session(session)
        return _render_html_result(
            title="✕ Server Resolution Error",
            status_code_name="server_not_resolved",
            message="Could not resolve the Discord server from the detected invite.",
            is_success=False,
            user_id=discord_user_id,
            session_id=session_id
        )

    # Step 7: Check membership via Arclent Discord Bot
    try:
        membership = await discord_service.check_guild_membership(
            guild_id=guild_id,
            user_id=discord_user_id
        )
    except discord_service.DiscordBotNotInServerError as dbne:
        logger.warning(f"[Discord Callback] Bot not in guild {guild_id}: {dbne.message}")
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "server_not_resolved"
        save_session(session)
        return _render_html_result(
            title="✕ Bot Not In Server",
            status_code_name="server_not_resolved",
            message=f"The Arclent Bot is not in '{guild_name}'. The server owner must add the bot to enable automated membership verification.",
            is_success=False,
            user_id=discord_user_id,
            guild_name=guild_name,
            invite_url=invite_url,
            session_id=session_id
        )
    except discord_service.DiscordBotAccessError as dbae:
        logger.warning(f"[Discord Callback] Bot lacks access in guild {guild_id}: {dbae.message}")
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "verification_error"
        save_session(session)
        return _render_html_result(
            title="✕ Bot Lacks Access",
            status_code_name="verification_error",
            message="The Arclent Bot lacks permission to access members in this Discord server.",
            is_success=False,
            user_id=discord_user_id,
            guild_name=guild_name,
            invite_url=invite_url,
            session_id=session_id
        )
    except discord_service.DiscordRateLimitError:
        return _render_html_result(
            title="✕ Discord Rate Limit",
            status_code_name="verification_error",
            message="Discord rate limit encountered. Please wait a moment and retry.",
            is_success=False,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"[Discord Callback] Guild membership check failed: {e}", exc_info=True)
        session.discord_user_id = discord_user_id
        session.discord_verification_status = "verification_error"
        save_session(session)
        return _render_html_result(
            title="✕ Verification Error",
            status_code_name="verification_error",
            message=f"Could not verify server membership: {str(e)}",
            is_success=False,
            user_id=discord_user_id,
            guild_name=guild_name,
            session_id=session_id
        )

    # Step 8: Finalize membership result
    is_member = membership.get("is_member", False)
    now_iso = datetime.now(timezone.utc).isoformat()

    session.discord_user_id = discord_user_id
    session.final_discord_user_id = discord_user_id
    session.discord_guild_id = guild_id
    session.discord_guild_name = guild_name
    session.discord_invite_url = invite_url

    if is_member:
        session.discord_verification_status = "verified"
        session.discord_verified_at = now_iso
        session.stage = OutreachStage.AUTO_VERIFIED
        session.creator_response = "confirmed"
        session.verified_at = now_iso

        if session.discord_profile:
            session.discord_profile.discord_user_id = discord_user_id
            session.discord_profile.discord_guild_id = guild_id
            session.discord_profile.discord_guild_name = guild_name
            session.discord_profile.discord_verification_status = "verified"
            session.discord_profile.discord_verified_at = now_iso
            session.discord_profile.status = "sendable"

        save_session(session)
        logger.info(f"Discord membership verified for session {session_id}, user {discord_user_id} in {guild_name}")

        return _render_html_result(
            title="Discord membership verified ✓",
            status_code_name="verified",
            message="You are a member of this Discord server.",
            is_success=True,
            guild_name=guild_name,
            user_id=discord_user_id,
            invite_url=invite_url,
            session_id=session_id
        )
    else:
        session.discord_verification_status = "not_verified"
        if session.discord_profile:
            session.discord_profile.discord_user_id = discord_user_id
            session.discord_profile.discord_guild_id = guild_id
            session.discord_profile.discord_guild_name = guild_name
            session.discord_profile.discord_verification_status = "not_verified"

        save_session(session)
        logger.info(f"Discord membership could not be verified for session {session_id}, user {discord_user_id} not in {guild_name}")

        return _render_html_result(
            title="Discord membership could not be verified.",
            status_code_name="not_verified",
            message="You are not currently a member of this Discord server.",
            is_success=False,
            guild_name=guild_name,
            user_id=discord_user_id,
            invite_url=invite_url,
            session_id=session_id
        )


# ------------------------------------------------------------------------------
# 3. Verification Status Endpoint
# ------------------------------------------------------------------------------

@router.get("/discord/verification-status", response_model=DiscordVerificationStatusResponse)
@router.get("/api/discord/verification-status", response_model=DiscordVerificationStatusResponse)
async def get_discord_verification_status(session_id: str = Query(...)):
    """Retrieve the persistent Discord server membership verification status for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session not found.")

    status_val = session.discord_verification_status or "pending"
    guild_name = session.discord_guild_name
    invite_url = _find_discord_invite_url(session)

    if status_val == "verified":
        message = "Discord membership verified ✓ You are a member of this Discord server."
    elif status_val == "not_verified":
        message = "Discord membership could not be verified. You are not currently a member of this Discord server."
    elif status_val == "server_not_resolved":
        message = "Discord server could not be resolved from the invite link."
    elif status_val == "oauth_failed":
        message = "Discord OAuth authentication failed or was cancelled."
    elif status_val == "verification_error":
        message = "An error occurred while verifying Discord server membership."
    else:
        message = "Verification pending."

    return DiscordVerificationStatusResponse(
        session_id=session.session_id,
        verified=(status_val == "verified"),
        discord_user_id=session.discord_user_id or session.final_discord_user_id,
        discord_guild_id=session.discord_guild_id,
        discord_invite_url=invite_url,
        discord_verification_status=status_val,
        discord_verified_at=session.discord_verified_at,
        guild_name=guild_name,
        message=message
    )


# ------------------------------------------------------------------------------
# 4. Set Discord User ID (from Other Discovered Profiles outreach selection)
# ------------------------------------------------------------------------------

@router.post("/discord/set-user-id")
@router.post("/api/discord/set-user-id")
async def set_discord_user_id(payload: SetDiscordUserIdRequest):
    """Set the creator's Discord User ID snowflake when user selects Discord outreach in other discovered profiles."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session not found.")

    clean_id = (payload.discord_user_id or "").strip()
    if not discord_service.validate_snowflake(clean_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid Discord User ID. A Discord User ID must be a 17-20 digit numeric snowflake (e.g. 803511102246789123)."
        )

    session.final_discord_user_id = clean_id
    session.discord_user_id = clean_id
    if session.discord_profile:
        session.discord_profile.discord_user_id = clean_id
        session.discord_profile.status = "sendable"

    save_session(session)
    return {
        "success": True,
        "session_id": session.session_id,
        "discord_user_id": clean_id
    }


# ------------------------------------------------------------------------------
# HTML Response Builder
# ------------------------------------------------------------------------------

def _render_html_result(
    title: str,
    status_code_name: str,
    message: str,
    is_success: bool,
    guild_name: Optional[str] = None,
    user_id: Optional[str] = None,
    invite_url: Optional[str] = None,
    session_id: Optional[str] = None
) -> HTMLResponse:
    """Render a clean, responsive HTML outcome card matching the Arclent design aesthetic."""
    badge_bg = "#00D26A" if is_success else "#FEF2F2"
    badge_color = "#000000" if is_success else "#991B1B"
    badge_border = "#111827" if is_success else "#EF4444"
    badge_text = "✓ VERIFIED" if is_success else "✕ NOT VERIFIED"
    icon_bg = "#00D26A" if is_success else "#EF4444"
    icon_char = "✓" if is_success else "✕"
    icon_color = "#000000" if is_success else "#FFFFFF"

    guild_html = f"""
        <div class="meta-row">
            <span class="meta-label">DISCORD SERVER</span>
            <span class="meta-value">{guild_name}</span>
        </div>
    """ if guild_name else ""

    user_html = f"""
        <div class="meta-row">
            <span class="meta-label">DISCORD USER ID</span>
            <span class="meta-value font-mono">{user_id}</span>
        </div>
    """ if user_id else ""

    action_button_html = ""
    if is_success:
        action_button_html = """
        <button type="button" class="btn-primary" onclick="handleFinish()">
            <span>Return to Arclent ✓</span>
        </button>
        """
    else:
        join_btn = f"""
        <a href="{invite_url}" target="_blank" rel="noopener noreferrer" class="btn-join">
            <span>Join Discord Server ↗</span>
        </a>
        """ if invite_url else ""
        retry_href = f"/discord/verify?session_id={session_id}" if session_id else "/"
        action_button_html = f"""
        <div class="btn-stack">
            {join_btn}
            <a href="{retry_href}" class="btn-retry">
                <span>🔄 Retry Verification</span>
            </a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Arclent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #FAF7F0;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px 16px;
        }}
        .card {{
            max-width: 480px;
            width: 100%;
            background: #FFFFFF;
            border: 2px solid #111827;
            box-shadow: 6px 6px 0px #111827;
            border-radius: 4px;
            padding: 36px 28px;
            text-align: center;
        }}
        .brand-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 14px;
            margin-bottom: 22px;
            border-bottom: 1.5px solid #E5E7EB;
        }}
        .brand-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border: 1.5px solid {badge_border};
            background: {badge_bg};
            color: {badge_color};
            border-radius: 2px;
        }}
        .icon-circle {{
            width: 52px;
            height: 52px;
            border-radius: 50%;
            background: {icon_bg};
            color: {icon_color};
            border: 2px solid #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: 800;
            margin: 0 auto 18px auto;
        }}
        h1 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 22px;
            font-weight: 800;
            margin-bottom: 10px;
            color: #111827;
        }}
        .body-desc {{
            font-size: 14px;
            color: #4B5563;
            line-height: 1.55;
            margin-bottom: 20px;
        }}
        .collab-meta-box {{
            background: #FAF8F2;
            border: 1.5px solid #111827;
            border-radius: 3px;
            padding: 12px 16px;
            margin-bottom: 22px;
            text-align: left;
        }}
        .meta-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px dashed #D1D5DB;
            font-size: 12.5px;
        }}
        .meta-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            font-weight: 700;
            color: #6B7280;
        }}
        .meta-value {{
            font-weight: 700;
            color: #111827;
        }}
        .font-mono {{
            font-family: 'JetBrains Mono', monospace;
        }}
        .btn-stack {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 18px;
        }}
        .btn-primary {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background: #00D26A;
            color: #000000;
            font-weight: 800;
            font-size: 14px;
            padding: 12px 18px;
            border: 2px solid #111827;
            border-radius: 3px;
            box-shadow: 3px 3px 0px #111827;
            cursor: pointer;
            text-decoration: none;
            transition: transform 0.1s ease;
        }}
        .btn-primary:hover {{
            transform: translate(-1px, -1px);
            box-shadow: 4px 4px 0px #111827;
        }}
        .btn-join {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background: #5865F2;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 13.5px;
            padding: 11px 16px;
            border: 2px solid #111827;
            border-radius: 3px;
            box-shadow: 3px 3px 0px #111827;
            text-decoration: none;
        }}
        .btn-join:hover {{
            background: #4752C4;
        }}
        .btn-retry {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background: #FFFFFF;
            color: #111827;
            font-weight: 700;
            font-size: 13px;
            padding: 10px 16px;
            border: 1.5px solid #111827;
            border-radius: 3px;
            text-decoration: none;
        }}
        .btn-retry:hover {{
            background: #F3F4F6;
        }}
        .footer-note {{
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: #9CA3AF;
            margin-top: 18px;
            padding-top: 12px;
            border-top: 1px solid #E5E7EB;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-header">
            <span class="brand-title">Arclent</span>
            <span class="status-badge">{badge_text}</span>
        </div>

        <div class="icon-circle">{icon_char}</div>
        <h1>{title}</h1>
        <p class="body-desc">{message}</p>

        <div class="collab-meta-box">
            {guild_html}
            {user_html}
            <div class="meta-row">
                <span class="meta-label">STATUS</span>
                <span class="meta-value font-mono">{status_code_name}</span>
            </div>
        </div>

        {action_button_html}

        <div class="footer-note">
            Discord Server Membership Auto-Verification • Arclent
        </div>
    </div>

    <script>
        // Post verification outcome to parent window if opened as popup
        const payload = {{
            type: 'DISCORD_VERIFY_RESULT',
            status: '{status_code_name}',
            is_member: {'true' if is_success else 'false'},
            guild_name: {f'"{guild_name}"' if guild_name else 'null'},
            user_id: {f'"{user_id}"' if user_id else 'null'},
            invite_url: {f'"{invite_url}"' if invite_url else 'null'},
            session_id: {f'"{session_id}"' if session_id else 'null'}
        }};

        if (window.opener) {{
            try {{
                window.opener.postMessage(payload, '*');
            }} catch (e) {{
                console.error("Could not postMessage to opener:", e);
            }}
        }}

        function handleFinish() {{
            if (window.opener) {{
                window.close();
            }} else {{
                window.location.href = '/';
            }}
        }}

        // Auto close after 3 seconds if successfully verified inside popup
        {'setTimeout(handleFinish, 3000);' if is_success else ''}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200 if is_success else 400)
