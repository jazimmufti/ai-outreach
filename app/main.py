"""Main FastAPI application entrypoint."""

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api import research, gmail, email, outreach

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

# Include API Routers
app.include_router(outreach.router)
app.include_router(research.router)
app.include_router(gmail.router)
app.include_router(email.router)

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
