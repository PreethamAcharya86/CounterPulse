from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class VoiceCommandRequest(BaseModel):
    transcript: str = Field(..., description="Spoken or typed user command")
    session_id: Optional[str] = Field(None, description="Optional conversational session ID")
    audio_base64: Optional[str] = Field(None, description="Optional base64 encoded audio input")
    synthesize: bool = Field(False, description="Whether to synthesize 24kHz audio via Gemini Live")

class VoiceCommandResponse(BaseModel):
    intent: str = Field(..., description="Parsed command intent")
    response_text: str = Field(..., description="Spoken/written voice assistant response")
    voice_state: str = Field("RESPONDING", description="IDLE, LISTENING, PROCESSING, RESPONDING, ERROR")
    requires_confirmation: bool = Field(False, description="Whether this command initiated a consequential action awaiting confirmation")
    pending_action: Optional[Dict[str, Any]] = Field(None, description="Action details awaiting confirmation")
    action_executed: Optional[str] = Field(None, description="Name of consequential action executed if confirmed")
    details: Optional[Dict[str, Any]] = Field(None, description="Contextual payload (e.g. case summary, report link)")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded 24kHz linear PCM synthesized speech from Gemini Live")

class VoiceSessionStatus(BaseModel):
    session_id: str
    case_id: str
    voice_state: str
    has_pending_action: bool
    pending_action: Optional[Dict[str, Any]] = None
