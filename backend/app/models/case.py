import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="Untitled Case")
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="intake")  # intake, analyzing, passport_ready, action_pending, resolved
    
    # Incident classification (from AI reconstruction)
    scam_category = Column(String(100), nullable=True)
    severity_level = Column(String(30), nullable=False, default="medium")  # low, medium, high, critical
    financial_loss = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="INR")
    modus_operandi = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan", order_by="Evidence.created_at")
    indicators = relationship("Indicator", back_populates="case", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan", order_by="TimelineEvent.order_index")
    compromise_assessments = relationship("CompromiseAssessment", back_populates="case", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="case", cascade="all, delete-orphan")
    actions = relationship("ActionEvent", back_populates="case", cascade="all, delete-orphan")
