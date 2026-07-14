
## Day 5 Progress Notes (In Progress)
- Reviewed AI/Product teammate's prompt architecture (extraction, timeline, fraud detection, complaint prompts)
- Decided: align extraction prompt to existing schema field names (no new migration for Phase 1)
- Decided: keep complaint generation template-based for Phase 1 (not AI-generated) for accuracy/reliability
- Next: build Timeline generation, then Fraud Detection with evidence completeness scoring (computed live, not stored)

## Known Limitations (Phase 1)
- **OCR failure mode #1:** Tesseract inconsistently misreads the ₹ symbol as other characters (%, F, ~, or stray digits), sometimes causing wrong amount extraction.
- **OCR failure mode #2 (found July 14):** Tesseract sometimes fails to read large/stylized amount text entirely (e.g. Google Pay's big-font ₹167 display), resulting in a correctly-null amount rather than a wrong one. Confirmed via case RESOLVE-2026-0025, evidence e6a30948-f6aa-4fb8-847f-589660b01cbc.
- PDF evidence upload is accepted but OCR/extraction is not implemented for PDFs — status stays "pending" indefinitely. Only image formats (jpg/jpeg/png) are processed.
- Timeline event timestamps are stored/returned in UTC; frontend does not currently convert to local timezone for display.
