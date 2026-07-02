import uuid
import enum
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class CaseStatus(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    complaint_generated = "complaint_generated"
    submitted = "submitted"
    closed = "closed"


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    case_number = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.draft, nullable=False)
    fraud_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships (let SQLAlchemy handle joins for you)
    owner = relationship("User", backref="cases")
    evidence_items = relationship("Evidence", backref="case", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", backref="case", cascade="all, delete-orphan")
    fraud_indicators = relationship("FraudIndicator", backref="case", cascade="all, delete-orphan")