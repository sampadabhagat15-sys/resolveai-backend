import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.evidence import FileType, OcrStatus


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    file_type: FileType
    original_filename: str
    ocr_status: OcrStatus
    ocr_raw_text: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True