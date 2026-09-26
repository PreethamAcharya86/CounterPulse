from fastapi import APIRouter
from backend.app.api.v1 import cases, evidence, analysis, reports, call_logs, voice

api_router = APIRouter()

# Include version 1 endpoints
api_router.include_router(cases.router, tags=["Cases"])
api_router.include_router(evidence.router, tags=["Evidence"])
api_router.include_router(analysis.router, tags=["AI Analysis & Intelligence"])
api_router.include_router(reports.router, tags=["Reports & Response"])
api_router.include_router(call_logs.router, tags=["Live Call Log & Intelligence"])
api_router.include_router(voice.router, tags=["Voice Control Layer"])
