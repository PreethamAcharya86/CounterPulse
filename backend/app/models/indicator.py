import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    indicator_type = Column(String(50), nullable=False)  # upi_id, phone_number, url, email, suspect_name, organization, account_number, transaction_id
    value = Column(Text, nullable=False)
    confidence = Column(String(20), nullable=False, default="medium")  # high, medium, low
    verification_status = Column(String(30), nullable=False, default="unverified")  # supported, possible, unverified, not_found
    source_evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    source_reference = Column(Text, nullable=True)  # quote or reference
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="indicators")
    source_evidence = relationship("Evidence", back_populates="indicators")
