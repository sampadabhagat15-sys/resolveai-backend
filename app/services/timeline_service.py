import json
from datetime import datetime
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


TIMELINE_PROMPT = """You are building a chronological fraud investigation timeline for a UPI dispute case. You will be given a list of evidence items belonging to the same case. Each item may include a timestamp, a source type such as SMS, screenshot, chat message, or user-written note, and any structured fields already extracted from it.

Rules you must follow strictly:

Arrange all evidence items in chronological order based on their timestamps, from earliest to latest. If two items share the exact same timestamp, order them in the sequence they were provided to you.

For each event, write one short, plain, factual sentence describing what happened. Base this only on the information given. Do not add interpretation, motive, or speculation about intent - describe what occurred, not why.

If an evidence item has no timestamp at all, do not guess where it belongs in the sequence. Instead place it separately in an unordered_events list.

If two evidence items appear to describe the same transaction from different sources, such as a bank SMS and a screenshot of the same payment confirmation, merge them into a single timeline event rather than duplicating it, and note that both sources confirm the same event.

Worked example:

Input evidence items:
[
  {{"timestamp": "2026-06-14T11:42:07", "source_type": "SMS", "extracted_fields": {{"amount": 4500, "beneficiary_upi_id": "fakeshop123@ybl"}}}},
  {{"timestamp": null, "source_type": "chat", "extracted_fields": {{}}, "raw_text": "Unknown: scan this QR to receive payment"}},
  {{"timestamp": "2026-06-14T11:53:41", "source_type": "SMS", "extracted_fields": {{"amount": 9800, "beneficiary_upi_id": "fakeshop123@ybl"}}}}
]

Correct output:
{{
  "timeline": [
    {{"timestamp": "2026-06-14T11:42:07", "event_summary": "An amount of Rs.4,500 was debited to VPA fakeshop123@ybl.", "source_type": "SMS"}},
    {{"timestamp": "2026-06-14T11:53:41", "event_summary": "A second debit of Rs.9,800 occurred to the same VPA, eleven minutes after the first.", "source_type": "SMS"}}
  ],
  "unordered_events": [
    {{"event_summary": "A chat message instructed the user to scan a QR code to receive a payment.", "source_type": "chat"}}
  ]
}}

Return your answer as valid JSON only, with no explanation or text outside the JSON. The structure must exactly match the format shown in the worked example above: a timeline list and an unordered_events list.

EVIDENCE ITEMS:
{evidence_list_json}
"""


def build_evidence_list_for_timeline(evidence_items_with_data, case_description=None):
    """
    evidence_items_with_data: list of tuples (Evidence, ExtractedData or None)
    case_description: the user's own written account of the fraud, if provided
    Returns a list of dicts matching the shape TIMELINE_PROMPT expects.
    """
    formatted = []

    if case_description:
        formatted.append({
            "timestamp": None,
            "source_type": "user_description",
            "extracted_fields": {},
            "raw_text": case_description,
        })

    for evidence, extracted in evidence_items_with_data:
        timestamp = None
        extracted_fields = {}

        if extracted:
            if extracted.transaction_date and extracted.transaction_time:
                timestamp = f"{extracted.transaction_date}T{extracted.transaction_time}"
            elif extracted.transaction_date:
                timestamp = f"{extracted.transaction_date}T00:00:00"

            extracted_fields = {
                "amount": float(extracted.amount) if extracted.amount is not None else None,
                "utr_number": extracted.utr_number,
                "merchant_name": extracted.merchant_name,
                "beneficiary_name": extracted.beneficiary_name,
                "beneficiary_upi_id": extracted.beneficiary_upi_id,
            }

        formatted.append({
            "timestamp": timestamp,
            "source_type": evidence.file_type.value,
            "extracted_fields": extracted_fields,
            "raw_text": evidence.ocr_raw_text or "",
        })
    return formatted


def generate_timeline(evidence_items_with_data, case_description=None) -> dict | None:
    evidence_list = build_evidence_list_for_timeline(evidence_items_with_data, case_description)

    if not evidence_list:
        return {"timeline": [], "unordered_events": []}

    try:
        prompt = TIMELINE_PROMPT.format(evidence_list_json=json.dumps(evidence_list))
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        return json.loads(raw_text)
    except Exception as e:
        print(f"Timeline generation failed: {e}")
        return None