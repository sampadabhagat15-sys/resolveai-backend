import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


def generate_complaint_pdf(complaint_text: str) -> bytes:
    """
    Takes the plain-text complaint and returns PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    body_style = styles["Normal"]
    body_style.fontSize = 11
    body_style.leading = 16

    story = []

    # Split into paragraphs on double newlines, preserve single newlines as <br/>
    paragraphs = complaint_text.split("\n\n")
    for para in paragraphs:
        formatted = para.replace("\n", "<br/>")
        story.append(Paragraph(formatted, body_style))
        story.append(Spacer(1, 12))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes