"""Gmail OAuth 2.0 API routes with PKCE and session state verification."""

import logging
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from app.models.schemas import GmailStatusResponse
from app.services.gmail_service import (
    get_gmail_status,
    generate_oauth_url,
    exchange_code_for_tokens,
    get_oauth_code_verifier,
    disconnect_gmail
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status", response_model=GmailStatusResponse)
async def check_gmail_status():
    """Get the current Gmail connection and sender profile status."""
    status = get_gmail_status()
    return GmailStatusResponse(
        connected=status.get("connected", False),
        email=status.get("email"),
        scopes=status.get("scopes")
    )


@router.get("/connect")
async def connect_gmail_endpoint(request: Request):
    """Initiate Google OAuth 2.0 connection flow with PKCE."""
    try:
        auth_url, state, code_verifier = generate_oauth_url()
        
        # Also store in HTTP session cookie if session middleware is active
        try:
            request.session["oauth_state"] = state
            request.session["oauth_code_verifier"] = code_verifier
        except Exception:
            pass

        return {"auth_url": auth_url, "state": state}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate Gmail connection: {str(e)}")


@router.get("/callback")
async def gmail_oauth_callback(
    request: Request,
    code: str = Query(None),
    error: str = Query(None),
    state: str = Query(None)
):
    """Handle the OAuth 2.0 callback from Google with PKCE validation."""
    if error:
        logger.warning(f"Google OAuth authorization rejected or failed: {error}")
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Connection Cancelled</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #FAF8F5; color: #121826; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                    .card {{ background: #fff; border: 2px solid #000; border-radius: 12px; padding: 32px; box-shadow: 4px 4px 0px #000; text-align: center; max-width: 440px; }}
                    .badge {{ background: #FEF2F2; color: #991B1B; font-weight: bold; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-bottom: 16px; border: 1.5px solid #000; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="badge">✕ CONNECTION CANCELLED</div>
                    <h2>Authorization Not Granted</h2>
                    <p style="color: #666; font-size: 14px; margin: 12px 0;">Google returned: {error}</p>
                    <p style="color: #888; font-size: 13px;">Closing this window and returning to app...</p>
                </div>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'GMAIL_AUTH_FAILED', error: '{error}' }}, '*');
                        setTimeout(() => window.close(), 2500);
                    }} else {{
                        setTimeout(() => window.location.href = '/', 2500);
                    }}
                </script>
            </body>
            </html>
            """,
            status_code=400
        )

    if not code or not state:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #FAF8F5;">
                <div style="background: #fff; border: 2px solid #000; border-radius: 12px; padding: 24px; max-width: 400px; margin: 0 auto; box-shadow: 4px 4px 0px #000;">
                    <h2>Invalid Callback Request</h2>
                    <p>Missing authorization code or state parameter.</p>
                    <a href="/" style="display: inline-block; margin-top: 12px; padding: 8px 16px; background: #00D26A; color: #000; text-decoration: none; border: 2px solid #000; font-weight: bold; border-radius: 6px;">Return to App</a>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )

    # Retrieve the PKCE code_verifier for this transaction
    code_verifier = get_oauth_code_verifier(state)
    if not code_verifier:
        # Fallback to session cookie
        try:
            sess_state = request.session.get("oauth_state")
            sess_verifier = request.session.get("oauth_code_verifier")
            if sess_state == state and sess_verifier:
                code_verifier = sess_verifier
        except Exception:
            pass

    if not code_verifier:
        logger.warning(f"OAuth session expired or state mismatch for state={state}")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Session Expired</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #FAF8F5; color: #121826; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                    .card { background: #fff; border: 2px solid #000; border-radius: 12px; padding: 32px; box-shadow: 4px 4px 0px #000; text-align: center; max-width: 440px; }
                    .badge { background: #FFFBEB; color: #92400E; font-weight: bold; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-bottom: 16px; border: 1.5px solid #000; }
                    .btn { display: inline-block; margin-top: 16px; padding: 10px 18px; background: #FFD028; color: #000; font-weight: bold; text-decoration: none; border: 2px solid #000; border-radius: 6px; box-shadow: 2px 2px 0px #000; }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="badge">⚠️ SESSION EXPIRED</div>
                    <h2>OAuth Session Timed Out</h2>
                    <p style="color: #666; font-size: 14px; margin: 12px 0;">
                        The verification token for this authorization attempt expired or was already used.
                    </p>
                    <p style="font-size: 13px; color: #4B5563;">
                        Please close this window and click <strong>"Connect Gmail"</strong> in the application to restart.
                    </p>
                    <a href="javascript:window.close();" class="btn">Close Window</a>
                </div>
                <script>
                    if (window.opener) {
                        window.opener.postMessage({ type: 'GMAIL_AUTH_FAILED', error: 'Session expired' }, '*');
                    }
                </script>
            </body>
            </html>
            """,
            status_code=400
        )

    try:
        # Perform token exchange with the original PKCE code_verifier
        status = exchange_code_for_tokens(code=code, state=state, code_verifier=code_verifier)
        user_email = status.get("email", "Connected Account")

        # Clean session cookie
        try:
            request.session.pop("oauth_state", None)
            request.session.pop("oauth_code_verifier", None)
        except Exception:
            pass

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Gmail Connected</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        background: #FAF8F5;
                        color: #121826;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background: #fff;
                        border: 2px solid #000;
                        border-radius: 12px;
                        padding: 32px;
                        box-shadow: 4px 4px 0px #000;
                        text-align: center;
                        max-width: 420px;
                    }}
                    .badge {{
                        background: #00D26A;
                        color: #000;
                        font-weight: bold;
                        padding: 6px 12px;
                        border-radius: 6px;
                        display: inline-block;
                        margin-bottom: 16px;
                        border: 1.5px solid #000;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="badge">✓ CONNECTED</div>
                    <h2>Gmail Account Linked!</h2>
                    <p style="margin: 12px 0;">Logged in as: <strong>{user_email}</strong></p>
                    <p style="color: #666; font-size: 13px;">Closing this window and returning to application...</p>
                </div>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'GMAIL_AUTH_SUCCESS', email: '{user_email}' }}, '*');
                        setTimeout(() => window.close(), 1200);
                    }} else {{
                        setTimeout(() => window.location.href = '/?gmail_connected=true', 1200);
                    }}
                </script>
            </body>
            </html>
            """
        )
    except Exception as e:
        logger.error(f"Error exchanging OAuth code: {e}", exc_info=True)
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Exchange Error</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #FAF8F5;">
                <div style="background: #fff; border: 2px solid #000; border-radius: 12px; padding: 24px; max-width: 440px; margin: 0 auto; box-shadow: 4px 4px 0px #000;">
                    <h2 style="color: #DC2626;">Token Exchange Failed</h2>
                    <p style="color: #666; font-size: 14px; margin: 12px 0;">{str(e)}</p>
                    <p style="font-size: 13px; color: #888;">Please close this window and try connecting again.</p>
                </div>
            </body>
            </html>
            """,
            status_code=500
        )


@router.post("/disconnect")
async def disconnect_gmail_endpoint(request: Request):
    """Disconnect stored Gmail credentials."""
    success = disconnect_gmail()
    try:
        request.session.clear()
    except Exception:
        pass
    return {"success": success, "message": "Gmail account disconnected successfully"}
