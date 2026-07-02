import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    source_evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True)

    event_time = Column(DateTime(timezone=True), nullable=True)
    event_description = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())