import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence, FileType, OcrStatus
from app.schemas.evidence import EvidenceResponse
from app.core.deps import get_current_user
from app.utils.file_utils import validate_file, save_upload_file
from app.services.ocr_service import extract_text_from_image
from typing import List

router = APIRouter(prefix="/evidence", tags=["Evidence"])

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

        # 5. Create DB record
        new_evidence = Evidence(
            case_id=case_id,
            file_path=file_path,
            file_type=file_type,
            original_filename=file.filename,
            ocr_status=ocr_status,
            ocr_raw_text=extracted_text,
        )
        db.add(new_evidence)
        created_evidence.append(new_evidence)

    db.commit()
    for evidence in created_evidence:
        db.refresh(evidence)

    return created_evidence