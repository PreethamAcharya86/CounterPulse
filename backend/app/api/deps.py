from backend.app.core.database import get_db
from backend.app.services.evidence_service import evidence_service, EvidenceService
from backend.app.services.orchestrator import ai_orchestrator, AIOrchestrator

def get_evidence_svc() -> EvidenceService:
    return evidence_service

def get_orchestrator() -> AIOrchestrator:
    return ai_orchestrator
