import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseResponse
from app.core.deps import get_current_user
from typing import List

router = APIRouter(prefix="/cases", tags=["Cases"])


def generate_case_number(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"RESOLVE-{year}-"

    # Count existing cases this year to determine the next sequence number
    count = db.query(func.count(Case.id)).filter(
        Case.case_number.like(f"{prefix}%")
    ).scalar()

    next_number = count + 1
    return f"{prefix}{next_number:04d}"  # e.g. RESOLVE-2026-0001


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_case = Case(
        user_id=current_user.id,
        case_number=generate_case_number(db),
        title=case_data.title,
        fraud_type=case_data.fraud_type,
        description=case_data.description,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case

@router.get("/", response_model=List[CaseResponse])
def list_my_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cases = db.query(Case).filter(
        Case.user_id == current_user.id,
        Case.is_deleted == False,
    ).order_by(Case.created_at.desc()).all()
    return cases