import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.call_log import (
    CallSessionCreate,
    CallSessionResponse,
    CallMessageCreate,
    CallMessageResponse,
    LiveExtractedIntelligence,
    PromoteCallResponse,
)
from backend.app.services.call_intelligence_service import (
    call_intelligence_service,
    CallIntelligenceService,
)

logger = logging.getLogger(__name__)

router = APIRouter()

def get_call_svc() -> CallIntelligenceService:
    return call_intelligence_service

@router.post("/cases/{case_id}/calls", response_model=CallSessionResponse, status_code=status.HTTP_201_CREATED)
def create_call_session(
    case_id: str,
    session_in: CallSessionCreate,
    db: Session = Depends(get_db),
    call_svc: CallIntelligenceService = Depends(get_call_svc),
):
    """Create a new Live Scam Call Session for a case."""
    try:
        session = call_svc.create_session(case_id=case_id, session_in=session_in, db=db)
        return call_svc.get_session_response(session)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error creating call session: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create call session: {str(e)}")

@router.get("/cases/{case_id}/calls", response_model=List[CallSessionResponse])
def list_call_sessions(
    case_id: str,
    db: Session = Depends(get_db),
    call_svc: CallIntelligenceService = Depends(get_call_svc),
):
    """List all call sessions for a case."""
    sessions = call_svc.list_sessions(case_id=case_id, db=db)
    return [call_svc.get_session_response(s) for s in sessions]

@router.get("/cases/{case_id}/calls/{call_id}", response_model=CallSessionResponse)
def get_call_session(
    case_id: str,
    call_id: str,
    db: Session = Depends(get_db),
    call_svc: CallIntelligenceService = Depends(get_call_svc),
):
    """Get a specific call session with full transcript and extracted intelligence."""
    try:
        session = call_svc.get_session(case_id=case_id, session_id=call_id, db=db)
        return call_svc.get_session_response(session)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/cases/{case_id}/calls/{call_id}/messages", response_model=CallSessionResponse)
async def add_call_message(
    case_id: str,
    call_id: str,
    msg_in: CallMessageCreate,
    db: Session = Depends(get_db),
    call_svc: CallIntelligenceService = Depends(get_call_svc),
):
    """
    Append a dialogue message to the call session and dynamically extract live intelligence.
    Extracts phone numbers, UPI IDs, URLs, emails, amounts, tactics, and claimed entities.
    """
    try:
        await call_svc.process_message(
            case_id=case_id,
            session_id=call_id,
            msg_in=msg_in,
            db=db,
        )
        session = call_svc.get_session(case_id=case_id, session_id=call_id, db=db)
        return call_svc.get_session_response(session)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error processing call message: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process message: {str(e)}")

@router.post("/cases/{case_id}/calls/{call_id}/promote", response_model=PromoteCallResponse)
def promote_call_session(
    case_id: str,
    call_id: str,
    db: Session = Depends(get_db),
    call_svc: CallIntelligenceService = Depends(get_call_svc),
):
    """
    Promote call transcript into the authoritative Evidence Vault.
    Maps all extracted indicators into case.indicators preserving forensic source provenance.
    """
    try:
        return call_svc.promote_to_case_evidence(case_id=case_id, session_id=call_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error promoting call session: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Promotion failed: {str(e)}")
