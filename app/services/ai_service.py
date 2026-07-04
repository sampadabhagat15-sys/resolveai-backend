import json
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


EXTRACTION_PROMPT = """You are analyzing OCR-extracted text from a screenshot related to a UPI (Unified Payments Interface) fraud case in India. The OCR text may be messy or contain errors.

Extract the following fields if present. Return ONLY valid JSON, no other text, no markdown formatting:

{{
  "amount": <number or null>,
  "utr_number": <string or null>,
  "transaction_date": <string in YYYY-MM-DD format or null>,
  "transaction_time": <string in HH:MM:SS format or null>,
  "merchant_name": <string or null>,
  "beneficiary_name": <string or null>,
  "beneficiary_upi_id": <string or null>,
  "confidence_score": <float between 0 and 1, your confidence in this extraction>
}}

If a field is not present or unclear in the text, use null for that field. Do not guess or fabricate values.

OCR TEXT:
{ocr_text}
"""


def extract_transaction_data(ocr_text: str) -> dict | None:
    """
    Sends OCR text to Gemini, returns extracted structured fields as a dict.
    Returns None if extraction fails or response isn't valid JSON.
    """
    if not ocr_text or not ocr_text.strip():
        return None

    try:
        prompt = EXTRACTION_PROMPT.format(ocr_text=ocr_text)
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Gemini sometimes wraps JSON in markdown code fences — strip those
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        data = json.loads(raw_text)
        return data
    except Exception as e:
        print(f"Gemini extraction failed: {e}")
        return None