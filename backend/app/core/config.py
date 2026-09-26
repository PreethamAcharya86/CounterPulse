import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_CURRENT_FILE = Path(__file__).resolve()
_REPO_ROOT = _CURRENT_FILE.parent.parent.parent.parent
_BACKEND_ROOT = _CURRENT_FILE.parent.parent.parent

# Load dotenv if available from candidate locations
for _p in (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env", Path.cwd() / ".env"):
    if _p.is_file():
        load_dotenv(dotenv_path=str(_p), override=False)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "CounterPulse AI"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    SECRET_KEY: str = "counterpulse-hackathon-insecure-secret-key-change-in-prod"
    
    # Database
    DATABASE_URL: str = "sqlite:///./counterpulse.db"
    
    # File Storage
    STORAGE_DIR: str = "./storage"
    
    # AI Provider Settings
    AI_PROVIDER: str = "gemini"  # gemini, openai, mock
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_LIVE_MODEL: str = "gemini-3.8-live"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    
    # Email Settings
    EMAIL_PROVIDER: str = "resend"
    RESEND_API_KEY: str = ""
    DEMO_RECIPIENT_EMAIL: str = "victim-recovery-demo@example.com"
    EMAIL_FROM: str = "CounterPulse Fraud Response <onboarding@resend.dev>"

settings = Settings()

# Ensure storage directory exists
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
