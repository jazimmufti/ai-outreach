"""Main FastAPI application entrypoint."""

import logging
from typing import Optional
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.config import settings
from app.api import research, gmail, email, outreach
from app.services.session_manager import get_most_recent_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("creator_outreach")

app = FastAPI(
    title="Arclent — Creator Discovery & Outreach Engine",
    description="Real YouTube Creator Discovery, Social Media Intelligence, and Gmail Outreach Platform",
    version="1.0.0"
)

# Session middleware for secure OAuth state & verifier cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="lax",
    https_only=False,  # Allow localhost development over HTTP
    max_age=900        # 15 minutes session TTL
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prevent browser caching of frontend static assets during development
@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include API Routers
app.include_router(outreach.router)
app.include_router(research.router)
app.include_router(gmail.router)
app.include_router(email.router)

# Top-level direct endpoint for Discord outreach
@app.post("/send-discord-message", response_model=outreach.SendDiscordMessageResponse, tags=["discord"])
async def send_discord_message_top_level(payload: outreach.SendDiscordMessageRequest):
    """Top-level direct endpoint to send outreach message via Arclent Discord Bot."""
    return await outreach.send_discord_message_endpoint(payload)

# Mount Frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the frontend single page app."""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(
                str(index_file),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        return {"status": "ok", "message": "Frontend index.html not found"}


@app.get("/verify", response_class=HTMLResponse)
async def verify_collaboration_root(
    session_id: Optional[str] = None,
    action: Optional[str] = None,
    token: Optional[str] = None
):
    """Top-level public verification endpoint for collaboration confirmation & rejection."""
    if not session_id:
        recent = get_most_recent_session()
        if recent:
            session_id = recent.session_id

    if not session_id:
        return HTMLResponse(
            content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Collaboration — Arclent</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
    <style>
        body { background-color: #FAF7F0; font-family: 'Plus Jakarta Sans', sans-serif; color: #111827; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { max-width: 440px; width: 100%; background: #FFFFFF; border: 2px solid #111827; box-shadow: 6px 6px 0px #111827; border-radius: 4px; padding: 36px 28px; text-align: center; }
        h2 { font-family: 'Space Grotesk', sans-serif; font-size: 22px; margin: 0 0 10px; }
        p { font-size: 14.5px; color: #4B5563; line-height: 1.5; margin: 0 0 20px; }
        a { display: inline-block; background: #00D26A; color: #000; text-decoration: none; font-weight: 700; padding: 10px 18px; border: 2px solid #111827; border-radius: 2px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Arclent Collaboration Verification</h2>
        <p>Please open the direct verification link provided in your collaboration confirmation message.</p>
        <a href="/">Go to Arclent Home</a>
    </div>
</body>
</html>""",
            status_code=400
        )
    return await outreach.handle_creator_verification_response(session_id=session_id, action=action, token=token)



@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    gmail_status = gmail.get_gmail_status()
    return {
        "status": "healthy",
        "mistral_configured": bool(settings.MISTRAL_API_KEY),
        "youtube_api_configured": bool(settings.YOUTUBE_API_KEY),
        "gmail_oauth_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "gmail_connected": gmail_status.get("connected", False),
        "environment": settings.ENVIRONMENT
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
