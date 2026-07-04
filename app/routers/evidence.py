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
        validate_file(file)
        file_path, stored_filename = save_upload_file(file, str(case_id))

        new_evidence = Evidence(
            case_id=case_id,
            file_path=file_path,
            file_type=file_type,
            original_filename=file.filename,
            ocr_status=OcrStatus.pending,
        )
        db.add(new_evidence)
        created_evidence.append(new_evidence)

    db.commit()
    for evidence in created_evidence:
        db.refresh(evidence)

    return created_evidence