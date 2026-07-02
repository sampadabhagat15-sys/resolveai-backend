import uuid
import enum
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class FileType(str, enum.Enum):
    screenshot = "screenshot"
    sms = "sms"
    chat_export = "chat_export"
    other = "other"


class OcrStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)

    file_path = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    original_filename = Column(String, nullable=False)

    ocr_raw_text = Column(Text, nullable=True)
    ocr_status = Column(Enum(OcrStatus), default=OcrStatus.pending, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    extracted_data_items = relationship("ExtractedData", backref="evidence", cascade="all, delete-orphan")