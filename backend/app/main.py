import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, run_migrations
import backend.app.models  # Ensures all ORM models are registered with Base
from backend.app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directory exists
    Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    # Create database tables if not existing
    Base.metadata.create_all(bind=engine)
    # Ensure newly added columns exist in existing SQLite databases
    run_migrations(engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="CounterPulse AI — Evidence-First Agentic Incident Response for Cyber-Fraud Victims",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware for Frontend React integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "version": "1.0.0",
        "api_docs": "/docs",
    }

@app.get(f"{settings.API_V1_PREFIX}/health")
def health_check():
    return {
        "status": "healthy",
        "database": "sqlite_connected",
        "storage_dir": os.path.exists(settings.STORAGE_DIR),
        "supported_evidence": ["image", "pdf", "text", "chat", "audio", "url"],
    }
