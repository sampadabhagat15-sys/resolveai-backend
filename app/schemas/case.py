import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel
from app.models.case import CaseStatus


class CaseCreate(BaseModel):
    title: str
    fraud_type: Optional[str] = None
    description: Optional[str] = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    case_number: str
    title: str
    status: CaseStatus
    fraud_type: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True