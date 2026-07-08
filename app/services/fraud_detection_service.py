import json
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


FRAUD_DETECTION_PROMPT = """You are a fraud analyst assistant reviewing the evidence timeline of a UPI dispute case to identify likely fraud patterns. You must be precise, evidence-based, and avoid assumptions, since these flags may be used in a formal complaint.

Pattern definitions - use these exact definitions, not general knowledge of scam types:

fake_qr_code_scam: the victim scanned a QR code believing they would receive a payment, but was instead prompted to enter their UPI PIN, resulting in an outgoing debit.

phishing_link: the victim clicked a link received by SMS, email, or message that impersonated a bank or official service, and entered login credentials or personal details on a fraudulent page.

impersonation_scam: the victim received a phone call or message from someone impersonating a bank official, customs officer, police officer, courier company, or similar authority, creating urgency to pressure a payment or an app installation. This applies regardless of the exact payment mechanism used afterwards.

kyc_update_scam: the victim was told their account or KYC status would be blocked or suspended, and was directed to a link or app to update it.

collect_request_scam: the victim received a UPI collect or payment request disguised as receiving money, a refund, or a reward, and approving it with their PIN actually sent money out of their account rather than receiving it.

remote_access_scam: the victim was asked to install a remote access application such as AnyDesk or TeamViewer, under the pretext of the caller needing to fix, verify, or secure their account.

fake_refund_scam: the victim was told they were owed a refund, reward, or cashback, and was asked to approve a request in order to receive it.

A single case may reasonably match more than one pattern at once - for example, a phone call impersonating customs staff that leads the victim to approve a collect request matches both impersonation_scam and collect_request_scam. Flag every pattern that genuinely applies, rather than forcing a single label.

For every pattern you flag, state which specific event in the timeline supports that conclusion. Do not flag a pattern based on general similarity alone - it must be traceable to specific evidence.

Also calculate an evidence_completeness_score from 0 to 100, reflecting how complete the current evidence is for filing a strong formal complaint. Base this on the presence of a UTR or transaction reference number, a clear amount, an exact date and time, beneficiary details, and a clear factual description of how the fraud occurred. List any specific missing evidence that would strengthen the case.

Worked example:

Input timeline:
{{
  "timeline": [
    {{"timestamp": "2026-06-22T10:02:00", "event_summary": "A phone call was received from a person claiming to be from the Delhi Customs Office, stating a parcel was seized and demanding a clearance fee.", "source_type": "call_log"}},
    {{"timestamp": "2026-06-22T10:05:44", "event_summary": "A collect request for Rs.2,999 from VPA customs.clearance@oksbi was approved, resulting in a debit.", "source_type": "SMS"}}
  ],
  "unordered_events": []
}}

Correct output:
{{
  "flagged_patterns": [
    {{"pattern": "impersonation_scam", "confidence": "high", "supporting_evidence": "A caller claimed to represent the Delhi Customs Office and demanded a clearance fee, a known impersonation tactic."}},
    {{"pattern": "collect_request_scam", "confidence": "high", "supporting_evidence": "A UPI collect request framed as a clearance fee was approved, resulting in an outgoing debit."}}
  ],
  "evidence_completeness_score": 65,
  "missing_evidence": ["Recording or transcript of the phone call", "Caller's phone number", "Any written communication from the caller"]
}}

This shows both patterns being flagged together correctly, since the evidence genuinely supports both.

Return your answer as valid JSON only, with no explanation or text outside the JSON, in the exact structure shown in the worked example above.

TIMELINE:
{timeline_json}
"""


def analyze_fraud_patterns(timeline_data: dict) -> dict | None:
    """
    timeline_data: dict with 'timeline' and 'unordered_events' keys
    (same shape as what generate_timeline() returns, or what GET /timeline provides)
    """
    try:
        prompt = FRAUD_DETECTION_PROMPT.format(timeline_json=json.dumps(timeline_data))
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        return json.loads(raw_text)
    except Exception as e:
        print(f"Fraud detection failed: {e}")
        return None