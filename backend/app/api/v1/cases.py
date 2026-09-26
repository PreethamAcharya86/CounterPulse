from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_passport_service, get_pdf_service
from backend.app.models.case import Case
from backend.app.schemas.case import CaseCreate, CaseResponse, CasePassportResponse, CaseUpdate
from backend.app.services.passport_service import PassportService, CaseNotFoundError, AnalysisNotReadyError
from backend.app.services.pdf_service import PDFReportService

router = APIRouter()

@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)):
    """Create a new fraud case."""
    case = Case(
        title=case_in.title,
        description=case_in.description,
        status="intake",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

@router.get("/cases", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    """List all cases."""
    return db.query(Case).order_by(Case.created_at.desc()).all()

@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get single case details."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
    return case

@router.patch("/cases/{case_id}", response_model=CaseResponse)
def update_case(case_id: str, case_in: CaseUpdate, db: Session = Depends(get_db)):
    """Update case status or description."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
    if case_in.title is not None:
        case.title = case_in.title
    if case_in.description is not None:
        case.description = case_in.description
    if case_in.status is not None:
        case.status = case_in.status
    db.commit()
    db.refresh(case)
    return case

@router.get("/cases/{case_id}/passport", response_model=CasePassportResponse)
def get_case_passport(
    case_id: str,
    db: Session = Depends(get_db),
    passport_svc: PassportService = Depends(get_passport_service),
):
    """
    Retrieve structured Fraud Case Passport aggregating dynamically generated CaseIntelligence.
    Preserves evidence provenance and factual audit trail.
    """
    try:
        return passport_svc.get_passport(case_id=case_id, db=db)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AnalysisNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate case passport: {str(e)}"
        )

@router.get("/cases/{case_id}/passport/pdf")
def get_case_passport_pdf(
    case_id: str,
    db: Session = Depends(get_db),
    passport_svc: PassportService = Depends(get_passport_service),
    pdf_svc: PDFReportService = Depends(get_pdf_service),
):
    """
    Generate and stream an official, high-fidelity PDF Fraud Case Passport dossier.
    """
    try:
        passport = passport_svc.get_passport(case_id=case_id, db=db)
        pdf_bytes = pdf_svc.generate_passport_pdf(passport)
        filename = f"CounterPulse_Case_{case_id}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AnalysisNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate passport PDF: {str(e)}"
        )

