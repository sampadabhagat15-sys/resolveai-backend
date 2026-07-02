import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Date, Time, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=True)
    utr_number = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=True)
    transaction_time = Column(Time, nullable=True)
    merchant_name = Column(String, nullable=True)
    beneficiary_name = Column(String, nullable=True)
    beneficiary_upi_id = Column(String, nullable=True)

    confidence_score = Column(Float, nullable=True)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())