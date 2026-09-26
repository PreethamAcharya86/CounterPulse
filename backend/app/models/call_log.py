import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(String(36), primary_key=True, default=lambda: f"CALL-{uuid.uuid4().hex[:8].upper()}")
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, default="Live Scam Call Session")
    caller_label = Column(String(100), nullable=False, default="Suspect / Impersonator")
    callee_label = Column(String(100), nullable=False, default="Victim / Callee")
    status = Column(String(30), nullable=False, default="active")  # active, completed, promoted
    raw_transcript = Column(Text, nullable=True)
    extracted_intelligence_json = Column(Text, nullable=True)
    evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="call_sessions")
    messages = relationship("CallMessage", back_populates="session", cascade="all, delete-orphan", order_by="CallMessage.message_index")
    evidence = relationship("Evidence")

class CallMessage(Base):
    __tablename__ = "call_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("call_sessions.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(String(50), nullable=False)  # caller, callee, system
    message_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    timestamp_offset = Column(String(20), nullable=True)  # e.g. "00:15"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("CallSession", back_populates="messages")
