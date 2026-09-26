import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_report_svc, get_email_provider_dep
from backend.app.schemas.report import (
    ReportResponse,
    ReportUpdate,
    ReportApproveRequest,
    ReportSendRequest,
    ReportGenerateResponse,
)
from backend.app.services.report_service import (
    ReportService,
    CaseNotFoundError,
    AnalysisNotReadyError,
    ReportNotFoundError,
    ReportAlreadySentError,
    ReportNotApprovedError,
)
from backend.app.services.email_service import (
    EmailProvider,
    EmailConfigurationError,
    EmailDispatchError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/cases/{case_id}/reports", response_model=List[ReportResponse])
def get_case_reports(
    case_id: str,
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Retrieve all response and incident reports for a case.
    If reports have not yet been instantiated, generates the initial AI drafts
    from CaseIntelligence without redundant LLM calls.
    """
    try:
        reports = report_svc.get_reports_for_case(case_id=case_id, db=db)
        return [ReportResponse.from_orm_model(r) for r in reports]
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AnalysisNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving reports for case %s: %s", case_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reports: {str(e)}",
        )

@router.post("/cases/{case_id}/reports/generate", response_model=ReportGenerateResponse)
def generate_reports(
    case_id: str,
    force: bool = Query(False, description="Whether to overwrite existing un-sent draft reports"),
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Generate or refresh structured response packages (Bank Dispute, Cybercrime Complaint, Security Advisory).
    Consumes pre-computed CaseIntelligence.
    """
    try:
        reports = report_svc.generate_draft_reports(
            case_id=case_id, db=db, force_regenerate=force
        )
        return ReportGenerateResponse(
            case_id=case_id,
            count=len(reports),
            reports=[ReportResponse.from_orm_model(r) for r in reports],
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AnalysisNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error generating reports for case %s: %s", case_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reports: {str(e)}",
        )

@router.get("/cases/{case_id}/reports/{report_id}", response_model=ReportResponse)
def get_single_report(
    case_id: str,
    report_id: str,
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Get a specific report by ID.
    """
    try:
        report = report_svc.get_report(case_id=case_id, report_id=report_id, db=db)
        return ReportResponse.from_orm_model(report)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}",
        )

@router.patch("/cases/{case_id}/reports/{report_id}", response_model=ReportResponse)
def update_report(
    case_id: str,
    report_id: str,
    update_data: ReportUpdate,
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Update or edit a draft report.
    Allows editing subject/title, markdown body, and recipient.
    If an already approved report is edited, its status resets to draft to prevent silent modification.
    """
    try:
        report = report_svc.update_draft_report(
            case_id=case_id, report_id=report_id, update_data=update_data, db=db
        )
        return ReportResponse.from_orm_model(report)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportAlreadySentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update report: {str(e)}",
        )

@router.post("/cases/{case_id}/reports/{report_id}/approve", response_model=ReportResponse)
def approve_report(
    case_id: str,
    report_id: str,
    approve_data: ReportApproveRequest = ReportApproveRequest(),
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Explicit human approval of a report draft.
    Marks status as 'approved' and records an audit event.
    """
    try:
        report = report_svc.approve_report(
            case_id=case_id,
            report_id=report_id,
            db=db,
            recipient_email=approve_data.recipient_email,
        )
        return ReportResponse.from_orm_model(report)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportAlreadySentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve report: {str(e)}",
        )

@router.post("/cases/{case_id}/reports/{report_id}/send", response_model=ReportResponse)
def send_report(
    case_id: str,
    report_id: str,
    send_data: ReportSendRequest = ReportSendRequest(),
    db: Session = Depends(get_db),
    report_svc: ReportService = Depends(get_report_svc),
    email_provider: EmailProvider = Depends(get_email_provider_dep),
):
    """
    Dispatch an approved report via email with optional Case Passport PDF attachment.
    CRITICAL SAFETY GATE: Rejects immediately (HTTP 400) if report is not explicitly approved.
    """
    try:
        report = report_svc.send_approved_report(
            case_id=case_id,
            report_id=report_id,
            db=db,
            recipient_email=send_data.recipient_email,
            attach_passport_pdf=send_data.attach_passport_pdf,
            email_provider=email_provider,
        )
        return ReportResponse.from_orm_model(report)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportNotApprovedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ReportAlreadySentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except EmailConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except EmailDispatchError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        logger.error("Unexpected dispatch error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dispatch failed: {str(e)}",
        )
