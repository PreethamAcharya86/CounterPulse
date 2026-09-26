import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False)  # bank_dispute, cybercrime_complaint, executive_passport
    title = Column(String(255), nullable=False)
    content_markdown = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)
    approval_status = Column(String(30), nullable=False, default="draft")  # draft, reviewed, approved, sent, failed
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    recipient_email = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    pdf_path = Column(String(512), nullable=True)
    evidence_references_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="reports")

class ActionEvent(Base):
    __tablename__ = "action_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)  # email_sent, pdf_generated, user_approval
    status = Column(String(30), nullable=False, default="pending")  # success, failed, pending
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="actions")
