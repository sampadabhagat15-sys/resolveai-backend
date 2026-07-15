# ResolveAI
### AI-Powered UPI Fraud Evidence & Dispute Resolution Platform

Built for the **MadeInIndia 2026 Hackathon** — Track ZAFD-005

**Live App:** [resolveai-frontend-eight.vercel.app](https://resolveai-frontend-eight.vercel.app/)
**Live API Docs:** [resolveai-backend-1.onrender.com/docs](https://resolveai-backend-1.onrender.com/docs)

---

## Problem Statement

> Victims of digital payment fraud often struggle to gather evidence and navigate complex dispute resolution processes, resulting in delayed outcomes.

When someone falls victim to UPI fraud, three things typically go wrong at once: panic and confusion about what evidence matters, uncertainty about whom to contact and in what order, and poorly structured complaints that slow down bank and cybercrime-portal investigations.

**ResolveAI** turns scattered evidence — screenshots, SMS, chats — into a structured, chronological, evidence-backed complaint, in minutes rather than hours, and guides the victim through the correct reporting sequence.

---

## What ResolveAI Does

1. **Create a fraud case** and describe what happened in your own words
2. **Upload evidence** — screenshots of transactions, SMS alerts, chat messages
3. **AI extracts transaction data automatically** — amount, UTR, date, time, merchant, beneficiary — via OCR + Gemini
4. **A chronological timeline is reconstructed** from all evidence, combining transaction data with your own account of events
5. **Fraud patterns are detected and flagged** — e.g. impersonation scam, fake QR code scam, collect request scam — each backed by specific evidence, not guesswork
6. **A formal complaint is generated** — combining verified facts, your narrative, and the detected fraud indicators — ready to copy into an email or download as a PDF to send to your bank

---

## How It Works

1. User signs up and logs in (JWT-based auth)
2. User creates a case with a title and a description of what happened
3. User uploads one or more evidence screenshots
4. Backend runs OCR (Tesseract) on each image to extract raw text
5. Gemini parses the OCR text into structured transaction fields, with a confidence score for each extraction
6. On request, Gemini builds a chronological timeline from all evidence *and* the case description
7. On request, Gemini analyzes the timeline against seven defined fraud patterns, flags any that are evidence-backed, and computes a live evidence-completeness score
8. A complaint letter is generated from a fixed, accuracy-first template — populated with the verified transaction facts, the user's narrative, and any detected fraud indicators
9. The user can copy the complaint text directly or download it as a formatted PDF

---

## System Architecture

![ResolveAI System Architecture](./docs/architecture.png)

The system is split into three layers:
- **Client:** React + Tailwind CSS frontend handling login, dashboard, case creation, evidence upload, timeline view, and report download
- **Backend:** FastAPI service with JWT authentication, orchestrating the OCR + AI pipeline and persisting all case data to PostgreSQL
- **OCR + AI Pipeline:** Tesseract OCR converts images to raw text; a three-stage Gemini 2.5 Flash pipeline (Extraction → Timeline → Fraud Detection) turns that raw text into structured, verified, and pattern-flagged case data

---

## Tech Stack

**Frontend:** React, Tailwind CSS, deployed on Vercel

**Backend:** FastAPI (Python), deployed on Render (Docker)

**Database:** PostgreSQL (Neon), managed via SQLAlchemy ORM + Alembic migrations

**Authentication:** JWT (JSON Web Tokens), bcrypt password hashing

**OCR:** Tesseract OCR (installed via Docker for production deployment)

**AI:** Google Gemini 2.5 Flash — three purpose-built prompts for extraction, timeline reconstruction, and fraud pattern detection

**PDF Generation:** ReportLab (template-based, not AI-generated, for factual accuracy in a legal-adjacent document)

---

## The AI Pipeline

ResolveAI uses a three-stage, chained AI pipeline — each stage's output feeds the next:

**① Extraction Prompt** *(runs once per uploaded evidence item)*
Takes raw OCR text and extracts `transaction_date`, `transaction_time`, `merchant_name`, `beneficiary_name`, `beneficiary_upi_id`, `utr_number`, `amount`, and a `confidence_score` reflecting extraction reliability. Never fabricates a value — returns `null` for anything not clearly present in the source text.

**② Timeline Prompt** *(runs once per case, after all evidence is extracted)*
Takes every evidence item's extracted data *and* the user's own written case description, and reconstructs a chronological sequence of events. Events without a clear timestamp are placed separately rather than guessed into position.

**③ Fraud Detection Prompt** *(runs once per case, after the timeline is built)*
Compares the full timeline against seven precisely defined fraud patterns — `fake_qr_code_scam`, `phishing_link`, `impersonation_scam`, `kyc_update_scam`, `collect_request_scam`, `remote_access_scam`, `fake_refund_scam` — flagging only patterns traceable to specific evidence. Also computes a live **evidence completeness score** (0–100) and lists specific missing evidence that would strengthen the case. This score and list are always computed fresh, never stored, so they reflect the case's current state.

**Complaint Generation** *(template-based, not AI-generated)*
Deliberately not an LLM-authored document. A fixed template is populated with verified facts from the pipeline above, ensuring the amount, UTR, and dates in a document sent to a bank are always exactly what's in the database — with zero risk of an AI subtly rephrasing or misstating a fact.

Full prompt text for every stage is maintained in [`docs/ai_prompts_detailed.py`](./docs/ai_prompts_detailed.py).

---

## Domain Grounding

- **RBI Zero Liability rule:** where the deficiency lies with the bank or a third party and the customer reports within 3 working days, liability is zero; reporting within 4–7 working days caps liability at a limited amount. Case creation timestamps support this logic.
- **NPCI UDIR escalation path:** complaints move from the App/PSP to the bank, then to NPCI for complex or fraud cases — reflected in the platform's case status model.
- **1930 helpline and cybercrime.gov.in:** the single most time-critical action for a fraud victim is calling 1930 immediately, since funds can often only be frozen mid-chain within a short window.
- **Evidence typically required:** UTR/transaction reference number, beneficiary VPA/account/merchant name, exact date and time, amount, screenshots of SMS/chat, and a factual description of the incident — this checklist directly shaped the extraction schema and evidence-completeness scoring.

Full domain research and requirements are documented in [`docs/ResolveAI_PRD.pdf`](./docs/ResolveAI_PRD.pdf).

---

## Testing

- Every backend endpoint was tested with real HTTP requests (curl) against real UPI transaction screenshots, not just assumed to work from code review
- Extraction accuracy was verified field-by-field against real screenshots
- Fraud detection was verified against both true positives (a real scam narrative correctly flagged with supporting evidence) and true negatives (legitimate-looking transactions correctly flagged as nothing)
- A complete end-to-end walkthrough was performed through the live deployed frontend — signup → case creation → evidence upload → timeline generation → fraud analysis → complaint generation → PDF download — confirming the full pipeline works for a real user, not just in isolated backend tests

---

## Documentation

- [Product Requirements Document (PRD)](./docs/ResolveAI_PRD.pdf) — problem statement, personas, user journey, scope, functional/non-functional requirements, domain grounding, and risks
- [AI Prompt Architecture](./docs/ai_prompts_detailed.py) — full text of the extraction, timeline, fraud detection, and complaint prompts, with worked examples

---

## Team

**Sampada Bhagat — Backend Lead**
Designed and built the full backend: database schema, authentication, case and evidence management, OCR integration, the three-stage AI pipeline (extraction, timeline, fraud detection), complaint generation, and production deployment. Owned all backend API contracts and coordinated integration with the frontend.

**Nikitha Harinath — Frontend Lead**
Designed and built the full React frontend: login/signup, dashboard, case creation and management flows, evidence upload, timeline and fraud analysis views, and complaint display/download — integrated end-to-end against the live backend API.

**Prajwal Mane — AI Engineer & Product Lead**
Designed the AI prompt architecture (extraction, timeline, and fraud detection prompts) with domain-grounded fraud pattern definitions, authored the Product Requirements Document, conducted OCR and extraction accuracy testing, and led product documentation, presentation, and demo preparation.

---

## Roadmap — Phase 2

- **Voice Input** — allow users to describe fraud incidents verbally
- **Multilingual Support** — extend evidence analysis and complaint generation to regional languages
- **Bank Dashboard** — a bank-side interface for reviewing and actioning submitted cases
- **RAG grounded in RBI/NPCI guideline documents** — so complaint language cites the correct clause directly from source material
- **Case Status Tracking** — mirroring the real App/PSP → Bank → NPCI → Ombudsman escalation ladder
- **Advanced Analytics** — aggregate fraud pattern trends across cases
- **"Call 1930 now" prompt** for cases created within 24–48 hours of the fraud date, surfacing the single most time-critical action for fund recovery
