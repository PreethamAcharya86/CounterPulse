from backend.app.core.database import get_db
from backend.app.services.evidence_service import evidence_service, EvidenceService
from backend.app.services.orchestrator import ai_orchestrator, AIOrchestrator
from backend.app.services.passport_service import passport_service, PassportService
from backend.app.services.pdf_service import pdf_report_service, PDFReportService

from backend.app.services.report_service import report_service, ReportService
from backend.app.services.email_service import get_email_provider, EmailProvider

def get_evidence_svc() -> EvidenceService:
    return evidence_service

def get_orchestrator() -> AIOrchestrator:
    return ai_orchestrator

def get_passport_service() -> PassportService:
    return passport_service

def get_pdf_service() -> PDFReportService:
    return pdf_report_service

def get_report_svc() -> ReportService:
    return report_service

def get_email_provider_dep() -> EmailProvider:
    return get_email_provider()

