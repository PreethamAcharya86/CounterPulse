from fastapi import APIRouter
from backend.app.api.v1 import cases, evidence, analysis

api_router = APIRouter()

# Include version 1 endpoints
api_router.include_router(cases.router, tags=["Cases"])
api_router.include_router(evidence.router, tags=["Evidence"])
api_router.include_router(analysis.router, tags=["AI Analysis & Intelligence"])
