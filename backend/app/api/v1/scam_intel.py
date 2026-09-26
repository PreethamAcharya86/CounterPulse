import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models.case import Case
from backend.app.models.indicator import Indicator
from backend.app.schemas.scam_intel import (
    ScamIntelligenceAnalyzeRequest,
    ScamIntelligenceAnalysisResponse,
    AddIndicatorsToCaseRequest,
    AddIndicatorsToCaseResponse,
    ScamIntelligenceItem,
    DISCLAIMER_TEXT,
)
from backend.app.services.scam_intel_service import scam_intel_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/cases/{case_id}/scam-intelligence/analyze",
    response_model=ScamIntelligenceAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_scam_intelligence(
    case_id: str,
    req: ScamIntelligenceAnalyzeRequest,
    db: Session = Depends(get_db),
):
    """
    Analyzes a conversation transcript or case evidence using regex extractors and
    the ScamIntelligenceAgent without hardcoding. Returns structured indicators with provenance.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' was not found in the incident vault.",
        )

    try:
        return await scam_intel_service.analyze_conversation(
            case_id=case_id,
            req=req,
            db=db,
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.exception("Error analyzing conversation intelligence for case %s: %s", case_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scam intelligence analysis failed: {str(e)}",
        )

@router.post(
    "/cases/{case_id}/scam-intelligence/add-to-case",
    response_model=AddIndicatorsToCaseResponse,
    status_code=status.HTTP_200_OK,
)
def add_scam_indicators_to_case(
    case_id: str,
    req: AddIndicatorsToCaseRequest,
    db: Session = Depends(get_db),
):
    """
    Merges selected extracted indicators into the case's authoritative Indicator table,
    avoiding duplicate creation and preserving source provenance.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' was not found in the incident vault.",
        )

    try:
        return scam_intel_service.add_indicators_to_case(
            case_id=case_id,
            indicators=req.indicators,
            evidence_id=req.evidence_id,
            db=db,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.exception("Error adding indicators to case %s: %s", case_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add indicators to case: {str(e)}",
        )

@router.get("/cases/{case_id}/scam-intelligence")
def get_case_scam_intelligence(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves existing case indicators and cached intelligence summary
    without triggering redundant AI calls.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' was not found in the incident vault.",
        )

    indicators = db.query(Indicator).filter(Indicator.case_id == case_id).all()
    items = [
        ScamIntelligenceItem(
            indicator_type=ind.indicator_type,
            value=ind.value,
            confidence=ind.confidence or "medium",
            verification_status=ind.verification_status or "unverified",
            source_reference=ind.source_reference or "Case Indicator Vault",
            source_evidence_id=ind.source_evidence_id,
        )
        for ind in indicators
    ]

    return {
        "case_id": case_id,
        "scam_category": case.scam_category or "Under Investigation",
        "severity_level": case.severity_level,
        "total_indicators": len(items),
        "indicators": items,
        "phone_numbers": [i for i in items if i.indicator_type == "phone_number"],
        "upi_ids": [i for i in items if i.indicator_type == "upi_id"],
        "urls": [i for i in items if i.indicator_type == "url"],
        "emails": [i for i in items if i.indicator_type == "email"],
        "disclaimer": DISCLAIMER_TEXT,
    }
