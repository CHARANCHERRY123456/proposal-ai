"""
Generate PDF from proposal draft text.
"""

import re
from io import BytesIO
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def remove_citations(text: str) -> str:
    """Remove citation markers like [1], [2], [1, 2, 3] from text for clean PDF output."""
    import re
    # Remove single citations [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)
    # Remove comma-separated citations [1, 2, 3], [1, 2, 3, 4, 5], etc.
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)
    # Clean up extra spaces that might be left
    text = re.sub(r'\s+', ' ', text)
    # Clean up spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    # Clean up multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def markdown_to_paragraphs(text: str, styles) -> list:
    """Convert markdown text to ReportLab Paragraph objects."""
    # Remove citations for clean professional PDF
    text = remove_citations(text)
    
    elements = []
    lines = text.split("\n")
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                elements.append(Paragraph(para_text, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
                current_paragraph = []
            continue
        
        # Check for headings
        if line.startswith("# "):
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                elements.append(Paragraph(para_text, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
                current_paragraph = []
            elements.append(Paragraph(line[2:], styles["Heading1"]))
            elements.append(Spacer(1, 0.2 * inch))
        elif line.startswith("## "):
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                elements.append(Paragraph(para_text, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
                current_paragraph = []
            elements.append(Paragraph(line[3:], styles["Heading2"]))
            elements.append(Spacer(1, 0.15 * inch))
        elif line.startswith("### "):
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                elements.append(Paragraph(para_text, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
                current_paragraph = []
            elements.append(Paragraph(line[4:], styles["Heading3"]))
            elements.append(Spacer(1, 0.1 * inch))
        elif line.startswith("- ") or line.startswith("* "):
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                elements.append(Paragraph(para_text, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
                current_paragraph = []
            # Bullet point - handle bold text properly
            bullet_text = line[2:].strip()
            # Replace **text** with <b>text</b>
            bullet_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', bullet_text)
            elements.append(Paragraph(f"• {bullet_text}", styles["Normal"]))
            elements.append(Spacer(1, 0.05 * inch))
        else:
            # Regular paragraph text - handle bold text properly
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            current_paragraph.append(line)
    
    # Add remaining paragraph
    if current_paragraph:
        para_text = " ".join(current_paragraph)
        elements.append(Paragraph(para_text, styles["Normal"]))
    
    return elements


def generate_pdf(draft_text: str, title: str = "Proposal Draft", company_name: Optional[str] = None) -> BytesIO:
    """
    Generate a PDF from draft text.
    Returns a BytesIO object containing the PDF data.
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor="black",
        spaceAfter=30,
        alignment=1,  # Center
    )
    
    heading1_style = ParagraphStyle(
        "CustomHeading1",
        parent=styles["Heading1"],
        fontSize=14,
        textColor="black",
        spaceAfter=12,
        spaceBefore=12,
    )
    
    heading2_style = ParagraphStyle(
        "CustomHeading2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor="black",
        spaceAfter=10,
        spaceBefore=10,
    )
    
    heading3_style = ParagraphStyle(
        "CustomHeading3",
        parent=styles["Heading3"],
        fontSize=11,
        textColor="black",
        spaceAfter=8,
        spaceBefore=8,
    )
    
    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor="black",
        leading=14,
        spaceAfter=6,
    )
    
    custom_styles = {
        "Title": title_style,
        "Heading1": heading1_style,
        "Heading2": heading2_style,
        "Heading3": heading3_style,
        "Normal": normal_style,
    }
    
    # Build story (content)
    story = []
    
    # Title
    story.append(Paragraph(title, custom_styles["Title"]))
    if company_name:
        story.append(Paragraph(company_name, custom_styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))
    
    # Convert markdown to paragraphs
    paragraphs = markdown_to_paragraphs(draft_text, custom_styles)
    story.extend(paragraphs)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
