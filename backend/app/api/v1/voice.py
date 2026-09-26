import logging
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_email_provider_dep
from backend.app.schemas.voice import VoiceCommandRequest, VoiceCommandResponse, VoiceSessionStatus
from backend.app.services.voice_service import voice_service, VoiceControlService
from backend.app.services.email_service import EmailProvider
from backend.app.core.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()

def get_voice_svc() -> VoiceControlService:
    return voice_service

@router.post("/cases/{case_id}/voice/command", response_model=VoiceCommandResponse)
async def handle_voice_command(
    case_id: str,
    cmd: VoiceCommandRequest,
    db: Session = Depends(get_db),
    voice_svc: VoiceControlService = Depends(get_voice_svc),
    email_provider: EmailProvider = Depends(get_email_provider_dep),
):
    """
    Process spoken or typed voice control command.
    Enforces strict confirmation gates for consequential actions (e.g. sending email).
    """
    try:
        return await voice_svc.execute_command(
            case_id=case_id,
            cmd=cmd,
            db=db,
            email_provider=email_provider,
        )
    except Exception as e:
        logger.error("Error executing voice command for case %s: %s", case_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice command processing failed: {str(e)}",
        )

@router.get("/cases/{case_id}/voice/session", response_model=VoiceSessionStatus)
def get_voice_session_status(
    case_id: str,
    session_id: Optional[str] = None,
    voice_svc: VoiceControlService = Depends(get_voice_svc),
):
    """Get current voice session state, active listeners, and pending confirmation."""
    return voice_svc.get_session_status(case_id=case_id, session_id=session_id)

@router.websocket("/cases/{case_id}/voice/live")
async def websocket_voice_live(
    websocket: WebSocket,
    case_id: str,
):
    """
    WebSocket endpoint for real-time bidirectional Gemini Live / voice streaming.
    Clients stream text or audio chunks and receive immediate state & response updates.
    """
    await websocket.accept()
    sess = voice_service.get_or_create_session(None, case_id)
    sess.voice_state = "LISTENING"

    # Send initial greeting & state
    await websocket.send_json({
        "type": "state_change",
        "voice_state": "LISTENING",
        "message": "CounterPulse Voice Layer active. Say 'Analyze this case' or 'What happened?'."
    })

    db = SessionLocal()
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            cmd_type = data.get("type", "voice_command")

            if cmd_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            transcript = data.get("transcript", "")
            if not transcript and "text" in data:
                transcript = data["text"]

            if not transcript:
                continue

            sess.voice_state = "PROCESSING"
            await websocket.send_json({"type": "state_change", "voice_state": "PROCESSING"})

            req = VoiceCommandRequest(
                transcript=transcript,
                session_id=sess.session_id,
                audio_base64=data.get("audio_base64"),
            )

            resp = await voice_service.execute_command(
                case_id=case_id,
                cmd=req,
                db=db,
            )

            await websocket.send_json({
                "type": "voice_response",
                "intent": resp.intent,
                "response_text": resp.response_text,
                "voice_state": resp.voice_state,
                "requires_confirmation": resp.requires_confirmation,
                "pending_action": resp.pending_action,
                "action_executed": resp.action_executed,
            })

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected for case %s", case_id)
        sess.voice_state = "IDLE"
    except Exception as e:
        logger.error("Voice WebSocket error: %s", e)
        sess.voice_state = "ERROR"
        try:
            await websocket.send_json({
                "type": "error",
                "voice_state": "ERROR",
                "message": f"Voice streaming error: {str(e)}",
            })
        except Exception:
            pass
    finally:
        db.close()
