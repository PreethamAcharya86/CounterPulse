import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_orchestrator
from backend.app.services.orchestrator import AIOrchestrator
from backend.app.services.agents.base import CaseContext
from backend.app.schemas.ai_output import CaseIntelligence, ScamIntelligenceOutput
from backend.app.models.case import Case

logger = logging.getLogger(__name__)

router = APIRouter()

class LiveAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Live text message or conversation chunk")
    user_authorized: bool = Field(..., description="Explicit user authorization for live analysis")
    sender: Optional[str] = None

@router.post("/cases/{case_id}/analyze", response_model=CaseIntelligence, status_code=status.HTTP_200_OK)
async def analyze_case(
    case_id: str,
    db: Session = Depends(get_db),
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
):
    """
    Trigger full multi-agent incident reconstruction, threat triage,
    scam intelligence, compromise assessment, and draft response package generation.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    try:
        intelligence = await orchestrator.analyze_case(
            case_id=case_id,
            db=db,
            persist_to_db=True,
        )
        return intelligence
    except Exception as e:
        logger.exception(f"AI Orchestration error on case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI incident orchestration failed: {str(e)}",
        )

@router.get("/cases/{case_id}/intelligence", response_model=CaseIntelligence)
async def get_case_intelligence(
    case_id: str,
    db: Session = Depends(get_db),
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
):
    """
    Retrieve structured multi-agent case intelligence.
    If not yet run, executes initial analysis and returns results.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    try:
        intelligence = await orchestrator.analyze_case(
            case_id=case_id,
            db=db,
            persist_to_db=True,
        )
        return intelligence
    except Exception as e:
        logger.exception(f"Failed to retrieve case intelligence for {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve case intelligence: {str(e)}",
        )

@router.post("/cases/{case_id}/agents/{agent_name}")
async def run_agent(
    case_id: str,
    agent_name: str,
    db: Session = Depends(get_db),
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
) -> Any:
    """
    Execute a specific specialized agent on demand.
    Available: evidence_intel, incident_reconstruction, triage, scam_intel, compromise, network_intel, response, followup.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    try:
        result = await orchestrator.run_single_agent(agent_name=agent_name, case_id=case_id, db=db)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error executing agent {agent_name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/live/analyze", response_model=ScamIntelligenceOutput)
async def analyze_live_chunk(
    payload: LiveAnalyzeRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
):
    """
    Fast-path intelligence analysis for live text chunks from Laptop 5 companion.
    Requires explicit user authorization.
    """
    if not payload.user_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live text analysis requires explicit user authorization."
        )

    context = CaseContext(
        case_id="LIVE_STREAM",
        title="Live Stream Analysis",
        description=f"Incoming message from {payload.sender or 'Unknown'}",
        combined_evidence_text=payload.text,
    )

    provider = orchestrator.get_provider()
    return await orchestrator.scam_intel_agent.run(context, provider)
