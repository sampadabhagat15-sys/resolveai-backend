import uuid
from datetime import datetime
from typing import List

from fastapi.responses import Response
from app.services.pdf_service import generate_complaint_pdf
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.extracted_data import ExtractedData
from app.schemas.case import CaseCreate, CaseResponse
from app.core.deps import get_current_user
from app.services.complaint_service import build_complaint_text

router = APIRouter(prefix="/cases", tags=["Cases"])


def generate_case_number(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"RESOLVE-{year}-"

    count = db.query(func.count(Case.id)).filter(
        Case.case_number.like(f"{prefix}%")
    ).scalar()

    next_number = count + 1
    return f"{prefix}{next_number:04d}"


def _compute_total_amount(db: Session, case_id: uuid.UUID):
    result = db.query(func.sum(ExtractedData.amount)).join(
        Evidence, ExtractedData.evidence_id == Evidence.id
    ).filter(
        Evidence.case_id == case_id,
        Evidence.is_deleted == False,
    ).scalar()
    return result


def _get_owned_case(db: Session, case_id: uuid.UUID, user: User) -> Case:
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user.id,
        Case.is_deleted == False,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _get_extracted_data_for_case(db: Session, case_id: uuid.UUID):
    return db.query(ExtractedData).join(
        Evidence, ExtractedData.evidence_id == Evidence.id
    ).filter(
        Evidence.case_id == case_id,
        Evidence.is_deleted == False,
    ).all()


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

    new_case.total_amount = _compute_total_amount(db, new_case.id)
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

    for case in cases:
        case.total_amount = _compute_total_amount(db, case.id)

    return cases


@router.get("/{case_id}/complaint")
def get_complaint_text(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    extracted_data_list = _get_extracted_data_for_case(db, case_id)

    complaint_text = build_complaint_text(case, extracted_data_list, current_user.full_name)
    return {"complaint_text": complaint_text}

@router.get("/{case_id}/complaint/pdf")
def get_complaint_pdf(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    extracted_data_list = _get_extracted_data_for_case(db, case_id)

    complaint_text = build_complaint_text(case, extracted_data_list, current_user.full_name)
    pdf_bytes = generate_complaint_pdf(complaint_text)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{case.case_number}_complaint.pdf"'
        },
    )