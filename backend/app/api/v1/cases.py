from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    get_db,
    get_passport_service,
    get_pdf_service,
    get_evidence_svc,
    get_orchestrator,
    get_report_svc,
)
from backend.app.models.case import Case
from backend.app.schemas.case import CaseCreate, CaseResponse, CasePassportResponse, CaseUpdate
from backend.app.services.passport_service import PassportService, CaseNotFoundError, AnalysisNotReadyError
from backend.app.services.pdf_service import PDFReportService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.orchestrator import AIOrchestrator
from backend.app.services.report_service import ReportService

router = APIRouter()

class DemoCaseRequest(BaseModel):
    scenario: Optional[str] = "digital_arrest"

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

@router.post("/cases/demo", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_demo_case(
    payload: Optional[DemoCaseRequest] = None,
    db: Session = Depends(get_db),
    evidence_svc: EvidenceService = Depends(get_evidence_svc),
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    report_svc: ReportService = Depends(get_report_svc),
):
    """
    Generate a full synthetic demonstration case with real dynamic multi-agent analysis.
    Provides realistic synthetic evidence input without requiring real victim PII,
    and executes the actual AI orchestration pipeline dynamically.
    No hardcoded AI outputs are used.
    """
    scenario = (payload.scenario if payload and payload.scenario else "digital_arrest").lower()

    if scenario == "power_disconnection":
        title = "Synthetic Demo: Electricity Disconnection & Malware Phishing"
        description = "Synthetic demonstration case: Victim received urgent power cutoff alert demanding APK installation and payment."
        convo_text = (
            "[18:30] Suspect: URGENT NOTICE from BESCOM Electricity Board: Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill of INR 4,850.\n"
            "[18:31] Victim: But I paid my monthly bill last week through the BESCOM portal!\n"
            "[18:32] Suspect: Last month update was not updated in our master server. Call officer Rajesh at 9845123456 immediately.\n"
            "[18:33] Suspect: Download our official QuickSupport verification update app from https://bescom-bill-update.cc/app.apk to clear status.\n"
            "[18:34] Suspect: Or pay immediate re-verification charge of ₹10 to bescom.recharge@oksbi to abort automated grid disconnection."
        )
        sms_text = "BESCOM Alert: Power supply will be disconnected tonight at 21:30 PM due to unpaid bill of INR 4,850. Call officer at 9845123456 or update at https://bescom-bill-update.cc"
        url = "https://bescom-bill-update.cc/app.apk"
    else:
        # Default: digital_arrest
        title = "Synthetic Demo: Digital Arrest & UPI Extortion Incident"
        description = "Synthetic demonstration case: Victim targeted by impersonator claiming to be Crime Branch officer alleging contraband in parcel, demanding ₹1,50,000 security deposit via ICICI UPI."
        convo_text = (
            "[10:01] Suspect: This is DCP Vikram from Delhi Police Crime Branch. You are under immediate digital arrest under Section 420/NDPS Act.\n"
            "[10:02] Suspect: Call our verification desk immediately at +91 98765 43210 or face physical remand within 2 hours.\n"
            "[10:03] Victim: Sir please, I am a school teacher in Bangalore! I have never ordered anything from Mumbai or abroad!\n"
            "[10:04] Suspect: A customs package in your name containing 140g of MDMA and 5 fake passports was intercepted at Mumbai Air Cargo.\n"
            "[10:05] Suspect: Supreme Court has issued high-priority search warrants. Stay on video call and do not disconnect under penalty of law.\n"
            "[10:06] Suspect: To prove your innocence, transfer an urgent verification security deposit of INR 1,50,000 to the statutory RBI holding account.\n"
            "[10:07] Suspect: Beneficiary UPI: clearance.vault@icici. Reference UTR will be generated automatically.\n"
            "[10:08] Suspect: Verify your clearance token at https://narcotics-case-clearance.gov-portal.org/clearance with case ID NDPS-8827."
        )
        sms_text = "INR 1,50,000.00 debited from A/c ending in 4321 on 26-SEP-26 via UPI Ref 987654321012 to clearance.vault@icici. If not you, report immediately to 1930."
        url = "https://narcotics-case-clearance.gov-portal.org/clearance"

    case = Case(
        title=title,
        description=description,
        status="intake",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # 1. Ingest synthetic chat conversation
    await evidence_svc.ingest_text(case_id=case.id, text=convo_text, db=db, evidence_type="chat")

    # 2. Ingest synthetic bank SMS
    await evidence_svc.ingest_text(case_id=case.id, text=sms_text, db=db, evidence_type="sms")

    # 3. Ingest synthetic URL
    await evidence_svc.ingest_url(case_id=case.id, url=url, db=db)

    # 4. Trigger REAL AI multi-agent orchestration dynamically
    await orchestrator.analyze_case(case_id=case.id, db=db, persist_to_db=True)

    # 5. Pre-instantiate draft response reports dynamically
    try:
        report_svc.get_reports_for_case(case_id=case.id, db=db)
    except Exception:
        pass

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

