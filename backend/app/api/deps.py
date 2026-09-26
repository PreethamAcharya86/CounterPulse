from backend.app.core.database import get_db
from backend.app.services.evidence_service import evidence_service, EvidenceService

def get_evidence_svc() -> EvidenceService:
    return evidence_service
