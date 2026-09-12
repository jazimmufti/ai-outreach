"""Application configuration settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    # AI / LLM (Mistral AI)
    MISTRAL_API_KEY: str = Field(default="", description="Mistral AI API key")
    GEMINI_API_KEY: str = Field(default="", description="Legacy Gemini API key fallback")

    
    # YouTube Data API
    YOUTUBE_API_KEY: str = Field(default="", description="YouTube Data API v3 key")
    
    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google OAuth Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/gmail/callback", 
        description="Google OAuth Redirect URI"
    )
    
    def is_redirect_uri_from_env(self) -> bool:
        """Check if GOOGLE_REDIRECT_URI is set explicitly in OS environment variables."""
        return "GOOGLE_REDIRECT_URI" in os.environ and bool(os.environ["GOOGLE_REDIRECT_URI"].strip())

    def get_redirect_uri(self) -> str:
        """Get sanitized Google Redirect URI prioritizing OS environment over .env file."""
        raw = os.environ.get("GOOGLE_REDIRECT_URI") or self.GOOGLE_REDIRECT_URI
        uri = str(raw).strip().strip("'\"")
        if uri.startswith("os.getenv") or not uri.startswith("http"):
            return "http://localhost:8000/api/gmail/callback"
        if uri.endswith("/api/gmail/callback/"):
            return uri[:-1]
        return uri

    def get_google_client_id(self) -> str:
        """Get sanitized Google Client ID stripped of whitespace and accidental quotes."""
        val = os.environ.get("GOOGLE_CLIENT_ID") or self.GOOGLE_CLIENT_ID
        return str(val).strip().strip("'\"")

    def get_google_client_secret(self) -> str:
        """Get sanitized Google Client Secret stripped of whitespace and accidental quotes."""
        val = os.environ.get("GOOGLE_CLIENT_SECRET") or self.GOOGLE_CLIENT_SECRET
        return str(val).strip().strip("'\"")

    
    # Discord Bot Integration
    DISCORD_BOT_TOKEN: str = Field(default="", description="Discord Bot Token for official API outreach")
    DISCORD_CLIENT_ID: str = Field(default="1548199535891972136", description="Discord Bot Application/Client ID")

    def get_discord_bot_token(self) -> str:
        """Get sanitized Discord Bot Token stripped of whitespace and accidental quotes."""
        val = os.environ.get("DISCORD_BOT_TOKEN") or self.DISCORD_BOT_TOKEN
        return str(val).strip().strip("'\"")

    def get_discord_client_id(self) -> str:
        """Get sanitized Discord Client ID."""
        val = os.environ.get("DISCORD_CLIENT_ID") or self.DISCORD_CLIENT_ID
        return str(val).strip().strip("'\"")

    # Session & Security
    SESSION_SECRET_KEY: str = Field(
        default="outreach_dev_secret_key_849204928173928172", 
        description="Session secret key"
    )
    
    # App config
    ENVIRONMENT: str = Field(default="development")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    TOKEN_FILE: str = Field(default=str(BASE_DIR / "token.json"))
    GMAIL_TOKEN_JSON: str = Field(default="", description="Optional JSON string of authorized Gmail tokens for serverless/Railway deployments")


    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton settings instance
settings = Settings()
