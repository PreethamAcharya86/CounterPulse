import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class CompromiseAssessment(Base):
    __tablename__ = "compromise_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)  # banking, credentials, remote_access, pii
    risk_level = Column(String(30), nullable=False, default="not_found")  # confirmed, possible, not_found, unverified
    details = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    source_evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="compromise_assessments")
    source_evidence = relationship("Evidence", back_populates="compromise_assessments")
