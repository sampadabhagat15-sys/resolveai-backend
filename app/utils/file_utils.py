import os
import uuid
from fastapi import UploadFile, HTTPException

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

UPLOAD_DIR = "uploads"


def validate_file(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def save_upload_file(file: UploadFile, case_id: str) -> tuple[str, str]:
    """Saves file to disk, returns (file_path, stored_filename)."""
    case_folder = os.path.join(UPLOAD_DIR, case_id)
    os.makedirs(case_folder, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    stored_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(case_folder, stored_filename)

    with open(file_path, "wb") as f:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Max size is 10MB.")
        f.write(content)

    return file_path, stored_filename