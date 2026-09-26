import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    
    # Email Settings
    EMAIL_PROVIDER: str = "resend"
    RESEND_API_KEY: str = ""
    DEMO_RECIPIENT_EMAIL: str = "victim-recovery-demo@example.com"
    EMAIL_FROM: str = "CounterPulse Fraud Response <onboarding@resend.dev>"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure storage directory exists
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
