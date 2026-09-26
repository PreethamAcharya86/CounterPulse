import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: f"EV-{uuid.uuid4().hex[:8].upper()}")
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # text, image, pdf, audio
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    file_path = Column(String(512), nullable=True)
    raw_content = Column(Text, nullable=True)  # extracted text or transcript
    sha256_hash = Column(String(64), nullable=True)
    processing_status = Column(String(50), nullable=False, default="uploaded")  # uploaded, processing, processed, failed
    normalized_json = Column(Text, nullable=True)  # JSON-encoded normalized evidence data
    error_message = Column(Text, nullable=True)    # Processing error details if failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="evidence")
    indicators = relationship("Indicator", back_populates="source_evidence", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="source_evidence")
    compromise_assessments = relationship("CompromiseAssessment", back_populates="source_evidence")
