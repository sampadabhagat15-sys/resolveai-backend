import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class FraudIndicator(Base):
    __tablename__ = "fraud_indicators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)

    indicator_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(Severity), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())