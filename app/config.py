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

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton settings instance
settings = Settings()
