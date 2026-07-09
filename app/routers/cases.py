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
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.core.deps import get_current_user
from app.services.complaint_service import build_complaint_text
from app.models.timeline_event import TimelineEvent
from app.services.timeline_service import generate_timeline
from app.models.fraud_indicator import FraudIndicator, Severity
from app.services.fraud_detection_service import analyze_fraud_patterns

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

@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: uuid.UUID,
    case_data: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)

    if case_data.title is not None:
        case.title = case_data.title
    if case_data.fraud_type is not None:
        case.fraud_type = case_data.fraud_type
    if case_data.description is not None:
        case.description = case_data.description

    db.commit()
    db.refresh(case)

    case.total_amount = _compute_total_amount(db, case.id)
    return case


@router.get("/{case_id}/complaint")
def get_complaint_text(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    extracted_data_list = _get_extracted_data_for_case(db, case_id)
    fraud_indicators = db.query(FraudIndicator).filter(FraudIndicator.case_id == case_id).all()

    complaint_text = build_complaint_text(case, extracted_data_list, current_user.full_name, fraud_indicators)
    return {"complaint_text": complaint_text}

@router.get("/{case_id}/complaint/pdf")
def get_complaint_pdf(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    extracted_data_list = _get_extracted_data_for_case(db, case_id)
    fraud_indicators = db.query(FraudIndicator).filter(FraudIndicator.case_id == case_id).all()

    complaint_text = build_complaint_text(case, extracted_data_list, current_user.full_name, fraud_indicators)
    pdf_bytes = generate_complaint_pdf(complaint_text)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{case.case_number}_complaint.pdf"'
        },
    )
@router.post("/{case_id}/timeline/generate")
def generate_case_timeline(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)

    evidence_items = db.query(Evidence).filter(
        Evidence.case_id == case_id,
        Evidence.is_deleted == False,
    ).all()

    evidence_items_with_data = []
    for evidence in evidence_items:
        extracted = db.query(ExtractedData).filter(
            ExtractedData.evidence_id == evidence.id
        ).first()
        evidence_items_with_data.append((evidence, extracted))

    timeline_result = generate_timeline(evidence_items_with_data, case_description=case.description)
    if timeline_result is None:
        raise HTTPException(status_code=500, detail="Timeline generation failed")

    # Clear any previously generated timeline for this case before saving new one
    db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()

    saved_events = []
    for event in timeline_result.get("timeline", []):
        ts = None
        if event.get("timestamp"):
            try:
                ts = datetime.fromisoformat(event["timestamp"])
            except ValueError:
                ts = None

        new_event = TimelineEvent(
            case_id=case_id,
            event_time=ts,
            event_description=event.get("event_summary", ""),
        )
        db.add(new_event)
        saved_events.append(new_event)

    for event in timeline_result.get("unordered_events", []):
        new_event = TimelineEvent(
            case_id=case_id,
            event_time=None,
            event_description=event.get("event_summary", ""),
        )
        db.add(new_event)
        saved_events.append(new_event)

    db.commit()

    return {
        "message": "Timeline generated successfully",
        "events_created": len(saved_events),
        "timeline": timeline_result.get("timeline", []),
        "unordered_events": timeline_result.get("unordered_events", []),
    }


@router.get("/{case_id}/timeline")
def get_case_timeline(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)

    events = db.query(TimelineEvent).filter(
        TimelineEvent.case_id == case_id
    ).order_by(TimelineEvent.event_time.asc().nullslast()).all()

    return [
        {
            "id": str(e.id),
            "event_time": e.event_time.isoformat() if e.event_time else None,
            "event_description": e.event_description,
        }
        for e in events
    ]
@router.post("/{case_id}/fraud-analysis")
def run_fraud_analysis(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)

    events = db.query(TimelineEvent).filter(
        TimelineEvent.case_id == case_id
    ).order_by(TimelineEvent.event_time.asc().nullslast()).all()

    if not events:
        raise HTTPException(
            status_code=400,
            detail="No timeline found for this case. Generate a timeline first."
        )

    timeline_list = []
    unordered_list = []
    for e in events:
        item = {"event_summary": e.event_description, "source_type": "evidence"}
        if e.event_time:
            item["timestamp"] = e.event_time.isoformat()
            timeline_list.append(item)
        else:
            unordered_list.append(item)

    timeline_data = {"timeline": timeline_list, "unordered_events": unordered_list}

    analysis = analyze_fraud_patterns(timeline_data)

    if analysis is None:
        raise HTTPException(status_code=500, detail="Fraud analysis failed")

    # Clear previous fraud indicators for this case before saving new ones
    db.query(FraudIndicator).filter(FraudIndicator.case_id == case_id).delete()

    saved_indicators = []
    for flagged in analysis.get("flagged_patterns", []):
        severity_str = flagged.get("confidence", "medium").lower()
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.medium

        indicator = FraudIndicator(
            case_id=case_id,
            indicator_type=flagged.get("pattern", "unknown"),
            description=flagged.get("supporting_evidence", ""),
            severity=severity,
        )
        db.add(indicator)
        saved_indicators.append(indicator)

    db.commit()

    return {
        "message": "Fraud analysis completed",
        "indicators_flagged": len(saved_indicators),
        "flagged_patterns": analysis.get("flagged_patterns", []),
        "evidence_completeness_score": analysis.get("evidence_completeness_score"),
        "missing_evidence": analysis.get("missing_evidence", []),
    }


@router.get("/{case_id}/fraud-indicators")
def get_fraud_indicators(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)

    indicators = db.query(FraudIndicator).filter(
        FraudIndicator.case_id == case_id
    ).all()

    return [
        {
            "id": str(i.id),
            "indicator_type": i.indicator_type,
            "description": i.description,
            "severity": i.severity.value,
        }
        for i in indicators
    ]