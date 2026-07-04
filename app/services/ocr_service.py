import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def extract_text_from_image(file_path: str) -> str | None:
    """
    Runs OCR on an image file and returns extracted text.
    Returns None if extraction fails (e.g. corrupted file, unsupported format).
    """
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed for {file_path}: {e}")
        return None