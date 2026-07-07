import json
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


EXTRACTION_PROMPT = """You are a financial data extraction assistant working for a UPI fraud reporting platform used by real fraud victims in India. You will be given raw OCR text extracted from a screenshot of a UPI transaction, a bank SMS alert, or a payment app notification. Your task is to extract specific structured fields from this text with complete accuracy, since this data may later be used in a formal complaint to a bank or the police.

Rules you must follow strictly:

Extract only the fields listed below. If a field is not clearly present in the text, return null for that field. Never guess, infer, or fabricate a value under any circumstances, even if it seems likely based on typical UPI message formats.

Normalise transaction_date to ISO format, written as YYYY-MM-DD, regardless of how it appears in the original text. If the year is written using only two digits, assume it belongs to the 2000s.

Normalise transaction_time to 24-hour format, written as HH:MM:SS. If seconds are not present in the source, use 00 for seconds. If no time is present at all, return null rather than inventing one.

If an amount appears with a currency symbol, the word Rs, or the word INR, extract only the numeric value as a number, not as text, and strip out commas. If the amount looks like it may contain an OCR misread, such as a letter O in place of a zero, still extract it exactly as written rather than silently correcting it, since a silent correction could hide a genuine OCR error that a human should review.

If the text contains more than one transaction, extract only the most recent or most complete one.

merchant_name refers to a recognisable business, shop, or service name if one is identifiable (for example, a shop name shown alongside a VPA). beneficiary_name refers to the name of the individual account holder receiving the payment, if shown separately from any business name. In many messages these will be the same value - in that case, populate both fields with it. If only one type of name is present, populate that field and return null for the other. Do not invent a merchant or beneficiary name that is not present in the text.

If the OCR text is garbled, incomplete, or does not contain a financial transaction at all, such as when it is actually a chat conversation with no transaction details, return all fields as null rather than forcing an answer, and set confidence_score accordingly (see below).

confidence_score is a number from 0 to 100 reflecting how reliable and complete this specific extraction is, based on how clearly the source text could be read and how many of the fields above could be confidently populated versus returned as null. A clean, fully legible message with every field present should score highly (90 to 100). A message where only one or two fields could be confidently extracted, or where the text was partially garbled, should score lower. A message with no transaction data at all should score close to 0. This score reflects the quality of this single piece of evidence, not the overall strength of the case.

Worked example 1 - a clean bank SMS:

Input OCR text:
Dear Customer, Rs.4500.00 debited from A/c XX3456 on 14-Jun-26 11:42:07 IST to VPA fakeshop123@ybl (Ramesh Traders). UPI Ref No 409823156712.

Correct output:
{{
  "transaction_date": "2026-06-14",
  "transaction_time": "11:42:07",
  "merchant_name": "Ramesh Traders",
  "beneficiary_name": "Ramesh Traders",
  "beneficiary_upi_id": "fakeshop123@ybl",
  "utr_number": "409823156712",
  "amount": 4500.00,
  "confidence_score": 95
}}

Worked example 2 - a chat message with no transaction data:

Input OCR text:
Unknown: bhaiya scan this QR to receive the payment for the order
Me: ok scanning

Correct output:
{{
  "transaction_date": null,
  "transaction_time": null,
  "merchant_name": null,
  "beneficiary_name": null,
  "beneficiary_upi_id": null,
  "utr_number": null,
  "amount": null,
  "confidence_score": 0
}}

This is the correct behaviour, not a failure - an empty result with a low confidence_score is right when no transaction data is present.

Return your answer as valid JSON only. Do not include any explanation, preamble, reasoning, or text outside the JSON object. Do not use markdown code fences. The JSON must follow exactly this structure:
{{
  "transaction_date": null,
  "transaction_time": null,
  "merchant_name": null,
  "beneficiary_name": null,
  "beneficiary_upi_id": null,
  "utr_number": null,
  "amount": null,
  "confidence_score": null
}}

OCR TEXT:
\"\"\"
{ocr_text}
\"\"\"
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

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        data = json.loads(raw_text)
        return data
    except Exception as e:
        print(f"Gemini extraction failed: {e}")
        return None