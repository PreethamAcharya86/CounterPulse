import os
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_evidence_svc
from backend.app.services.evidence_service import EvidenceService
from backend.app.models.evidence import Evidence
from backend.app.models.case import Case
from backend.app.schemas.evidence import (
    EvidenceResponse,
    TextEvidenceUpload,
    ChatEvidenceUpload,
    URLEvidenceUpload,
    LiveTextChunkUpload,
    EvidenceProcessResponse,
)
from backend.app.core.security import sanitize_path_for_response

logger = logging.getLogger(__name__)

router = APIRouter()

def _format_evidence_response(ev: Evidence) -> EvidenceResponse:
    """Helper to convert ORM model to EvidenceResponse without leaking internal filesystem paths."""
    norm_dict = None
    if ev.normalized_json:
        try:
            norm_dict = json.loads(ev.normalized_json)
        except Exception:
            norm_dict = None

    return EvidenceResponse(
        id=ev.id,
        case_id=ev.case_id,
        evidence_type=ev.evidence_type,
        filename=ev.filename,
        mime_type=ev.mime_type,
        file_size=ev.file_size,
        file_path=sanitize_path_for_response(ev.file_path) if ev.file_path else None,
        raw_content=ev.raw_content,
        sha256_hash=ev.sha256_hash,
        processing_status=ev.processing_status,
        normalized_data=norm_dict,
        error_message=ev.error_message,
        created_at=ev.created_at,
    )

@router.post("/cases/{case_id}/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    evidence_type: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """
    Primary evidence upload endpoint supporting:
    1. Multipart file upload (images, PDFs, audio, text files)
    2. Form-encoded raw text / SMS
    3. Form-encoded URL
    """
    # 1. URL upload
    if url and url.strip():
        ev, _ = await service.ingest_url(case_id=case_id, url=url, db=db)
        return _format_evidence_response(ev)

    # 2. Text upload
    if text and text.strip():
        ev_type = evidence_type or "text"
        ev, _ = await service.ingest_text(case_id=case_id, text=text, db=db, evidence_type=ev_type)
        return _format_evidence_response(ev)

    # 3. File upload
    if file:
        ev, _ = await service.ingest_file(
            case_id=case_id,
            file=file,
            db=db,
            evidence_type_override=evidence_type,
            auto_process=True,
        )
        return _format_evidence_response(ev)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No evidence provided. Submit a file, text string, or url.",
    )

@router.post("/cases/{case_id}/evidence/text", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_text_evidence(
    case_id: str,
    payload: TextEvidenceUpload,
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """Explicit JSON endpoint to ingest incident narratives or Bank SMS."""
    ev_type = payload.evidence_type or "text"
    ev, _ = await service.ingest_text(
        case_id=case_id,
        text=payload.text,
        db=db,
        evidence_type=ev_type,
        description=payload.description,
    )
    return _format_evidence_response(ev)

@router.post("/cases/{case_id}/evidence/chat", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_chat_evidence(
    case_id: str,
    payload: ChatEvidenceUpload,
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """Explicit JSON endpoint to ingest WhatsApp/Telegram chat logs."""
    ev, _ = await service.ingest_text(
        case_id=case_id,
        text=payload.chat_text,
        db=db,
        evidence_type="chat",
        description=payload.description,
    )
    return _format_evidence_response(ev)

@router.post("/cases/{case_id}/evidence/url", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_url_evidence(
    case_id: str,
    payload: URLEvidenceUpload,
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """Explicit JSON endpoint to ingest suspicious links as unverified evidence."""
    ev, _ = await service.ingest_url(
        case_id=case_id,
        url=payload.url,
        db=db,
        description=payload.description,
    )
    return _format_evidence_response(ev)

@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
async def list_case_evidence(
    case_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all evidence items attached to a specific case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    items = db.query(Evidence).filter(Evidence.case_id == case_id).order_by(Evidence.created_at.desc()).all()
    return [_format_evidence_response(item) for item in items]

@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details, normalized data, and provenance for a single evidence item."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return _format_evidence_response(ev)

@router.get("/evidence/{evidence_id}/file")
async def get_evidence_file(
    evidence_id: str,
    db: Session = Depends(get_db),
):
    """Serve the raw stored evidence file (image, pdf, text, audio) for inspection."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev or not ev.file_path or not os.path.exists(ev.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File for evidence '{evidence_id}' not found.")
    return FileResponse(ev.file_path, media_type=ev.mime_type, filename=ev.filename)

@router.post("/evidence/{evidence_id}/process", response_model=EvidenceProcessResponse)
async def process_or_retry_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """
    Trigger or re-try processing for an evidence item.
    Enforces real processing without fake status.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    normalized = await service.process_evidence_record(evidence_id=evidence_id, db=db)
    
    char_count = len(normalized.to_db_content())
    segment_count = len(normalized.content.get("segments", []))

    return EvidenceProcessResponse(
        evidence_id=ev.id,
        processing_status=ev.processing_status,
        evidence_type=ev.evidence_type,
        character_count=char_count,
        segment_count=segment_count,
        normalized_data=normalized.model_dump(),
        error_message=ev.error_message,
    )

@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
):
    """Delete an evidence record and securely remove stored file if present."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    if ev.file_path and os.path.exists(ev.file_path):
        try:
            os.remove(ev.file_path)
        except Exception as e:
            logger.warning(f"Could not remove file {ev.file_path}: {e}")

    db.delete(ev)
    db.commit()
    return None

@router.post("/live/text", response_model=EvidenceResponse)
async def ingest_live_text(
    payload: LiveTextChunkUpload,
    db: Session = Depends(get_db),
    service: EvidenceService = Depends(get_evidence_svc),
):
    """
    Endpoint for Laptop 5 companion to stream authorized live WhatsApp text chunks.
    Requires explicit user authorization flag.
    """
    if not payload.user_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live WhatsApp text ingestion requires explicit user authorization."
        )

    # If case_id is omitted, find latest active case or create a default live case
    case_id = payload.case_id
    if not case_id:
        latest_case = db.query(Case).order_by(Case.created_at.desc()).first()
        if latest_case:
            case_id = latest_case.id
        else:
            new_case = Case(title="Live WhatsApp Incident", description="Auto-created from live companion stream")
            db.add(new_case)
            db.commit()
            db.refresh(new_case)
            case_id = new_case.id

    try:
        ev, _ = await service.ingest_live_chunk(
            case_id=case_id,
            chunk_text=payload.chunk_text,
            user_authorized=payload.user_authorized,
            db=db,
            sender=payload.sender,
            timestamp=payload.timestamp,
            source_device=payload.source_device,
        )
        return _format_evidence_response(ev)
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
