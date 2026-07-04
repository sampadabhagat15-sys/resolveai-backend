import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence, FileType, OcrStatus
from app.models.extracted_data import ExtractedData
from app.schemas.evidence import EvidenceResponse
from app.core.deps import get_current_user
from app.utils.file_utils import validate_file, save_upload_file
from app.services.ocr_service import extract_text_from_image
from app.services.ai_service import extract_transaction_data

router = APIRouter(prefix="/evidence", tags=["Evidence"])


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_time(time_str):
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except (ValueError, TypeError):
        return None


@router.post("/upload", response_model=List[EvidenceResponse], status_code=status.HTTP_201_CREATED)
def upload_evidence(
    case_id: uuid.UUID = Form(...),
    file_type: FileType = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Confirm the case exists AND belongs to this user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == current_user.id,
        Case.is_deleted == False,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")

    created_evidence = []

    for file in files:
        # 2. Validate each file
        validate_file(file)

        # 3. Save to disk
        file_path, stored_filename = save_upload_file(file, str(case_id))

        # 4. Run OCR immediately (images only, for now)
        ext = file.filename.lower().rsplit(".", 1)[-1]
        if ext in ("jpg", "jpeg", "png"):
            extracted_text = extract_text_from_image(file_path)
            ocr_status = OcrStatus.completed if extracted_text is not None else OcrStatus.failed
        else:
            extracted_text = None
            ocr_status = OcrStatus.pending  # PDFs: OCR not yet implemented

        # 5. Create DB record for the evidence file itself
        new_evidence = Evidence(
            case_id=case_id,
            file_path=file_path,
            file_type=file_type,
            original_filename=file.filename,
            ocr_status=ocr_status,
            ocr_raw_text=extracted_text,
        )
        db.add(new_evidence)
        db.flush()  # assigns new_evidence.id without committing yet
        created_evidence.append(new_evidence)

        # 6. If OCR succeeded, run Gemini extraction and save structured fields
        if ocr_status == OcrStatus.completed and extracted_text:
            ai_result = extract_transaction_data(extracted_text)
            if ai_result:
                extracted_record = ExtractedData(
                    evidence_id=new_evidence.id,
                    amount=ai_result.get("amount"),
                    utr_number=ai_result.get("utr_number"),
                    transaction_date=_parse_date(ai_result.get("transaction_date")),
                    transaction_time=_parse_time(ai_result.get("transaction_time")),
                    merchant_name=ai_result.get("merchant_name"),
                    beneficiary_name=ai_result.get("beneficiary_name"),
                    beneficiary_upi_id=ai_result.get("beneficiary_upi_id"),
                    confidence_score=ai_result.get("confidence_score"),
                )
                db.add(extracted_record)

    db.commit()
    for evidence in created_evidence:
        db.refresh(evidence)

    return created_evidence