from datetime import datetime


COMPLAINT_TEMPLATE = """To,
The Grievance Redressal Officer,
[Bank/UPI Service Provider]

Subject: Unauthorised UPI Transaction(s) — Case Reference {case_number}

Dear Sir/Madam,

I am writing to report {transaction_intro} that occurred without my authorisation, as detailed below:

{transaction_details}

{description_section}{fraud_indicators_section}I request an immediate investigation into this matter and appropriate action, including reversal of the disputed amount(s), under the RBI's Limited Liability guidelines for unauthorised electronic transactions.

I am attaching supporting evidence (screenshots, messages) that substantiate this complaint. Please treat this as a formal, time-sensitive request given the nature of the fraud involved.

I look forward to your prompt response and resolution.

Regards,
{user_name}
Case Reference: {case_number}
Date of Complaint: {complaint_date}
"""


def build_complaint_text(case, extracted_data_list, user_name: str, fraud_indicators=None) -> str:
    meaningful_count = sum(
        1 for tx in extracted_data_list
        if any([tx.amount is not None, tx.utr_number, tx.transaction_date, tx.transaction_time, tx.merchant_name, tx.beneficiary_upi_id])
    )
    if meaningful_count == 1:
        transaction_intro = "an unauthorised UPI transaction"
    elif meaningful_count > 1:
        transaction_intro = f"{meaningful_count} unauthorised UPI transactions"
    else:
        transaction_intro = "unauthorised activity on my account"

    if extracted_data_list:
        blocks = []
        tx_number = 0
        for tx in extracted_data_list:
            # Skip entries with no meaningful extracted data at all
            has_any_data = any([
                tx.amount is not None,
                tx.utr_number,
                tx.transaction_date,
                tx.transaction_time,
                tx.merchant_name,
                tx.beneficiary_upi_id,
            ])
            if not has_any_data:
                continue

            tx_number += 1
            lines = [f"Transaction {tx_number}:"]
            if tx.amount is not None:
                lines.append(f"  - Amount: Rs. {tx.amount}")
            if tx.utr_number:
                lines.append(f"  - UTR Number: {tx.utr_number}")
            if tx.transaction_date:
                lines.append(f"  - Date: {tx.transaction_date}")
            if tx.transaction_time:
                lines.append(f"  - Time: {tx.transaction_time}")
            if tx.merchant_name:
                lines.append(f"  - Merchant/Payee: {tx.merchant_name}")
            if tx.beneficiary_upi_id:
                lines.append(f"  - Beneficiary UPI ID: {tx.beneficiary_upi_id}")
            blocks.append("\n".join(lines))

        transaction_details = "\n\n".join(blocks) if blocks else "No transaction details have been extracted yet for this case."
    else:
        transaction_details = "No transaction details have been extracted yet for this case."

    description_section = ""
    if case.description:
        description_section = f"Additional details: {case.description}\n\n"

    fraud_indicators_section = ""
    if fraud_indicators:
        pattern_names = {
            "fake_qr_code_scam": "Fake QR Code Scam",
            "phishing_link": "Phishing Link",
            "impersonation_scam": "Impersonation Scam",
            "kyc_update_scam": "KYC Update Scam",
            "collect_request_scam": "Collect Request Scam",
            "remote_access_scam": "Remote Access Scam",
            "fake_refund_scam": "Fake Refund Scam",
        }
        lines = ["Fraud Indicators Identified:\n"]
        for indicator in fraud_indicators:
            readable_name = pattern_names.get(indicator.indicator_type, indicator.indicator_type)
            lines.append(f"- {readable_name} ({indicator.severity.value} confidence): {indicator.description}")
        fraud_indicators_section = "\n".join(lines) + "\n\n"

    return COMPLAINT_TEMPLATE.format(
        case_number=case.case_number,
        transaction_intro=transaction_intro,
        transaction_details=transaction_details,
        description_section=description_section,
        fraud_indicators_section=fraud_indicators_section,
        user_name=user_name,
        complaint_date=datetime.utcnow().strftime("%d %B %Y"),
    )