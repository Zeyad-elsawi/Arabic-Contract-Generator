"""Export a structured contract to DOCX and PDF, both right-to-left.

DOCX
----
``python-docx`` natively supports RTL paragraphs via the ``w:bidi`` element.
We set it on every paragraph and on the section so Word/LibreOffice opens
the file with proper Arabic alignment.

PDF
---
``reportlab`` does not shape Arabic letters by default. We pre-shape the
text using ``arabic_reshaper`` and reorder it with ``python-bidi`` before
drawing. A bundled font is required for Arabic glyphs; we try common
system fonts (Arial, Tahoma, Times New Roman) which ship with Windows and
support the full Arabic Unicode range.
"""

from __future__ import annotations

import io
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

from schema import DraftedContract


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
def _set_rtl(paragraph) -> None:
    """Flip a paragraph to right-to-left."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        from docx.oxml import OxmlElement
        bidi = OxmlElement("w:bidi")
        pPr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _add_arabic_paragraph(
    doc: Document,
    text: str,
    *,
    bold: bool = False,
    size: int = 12,
    align_center: bool = False,
    font: str = "Arial",
) -> None:
    p = doc.add_paragraph()
    _set_rtl(p)
    if align_center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    # python-docx needs the East-Asian font hint to apply to non-Latin scripts
    rPr = run._element.get_or_add_rPr()
    from docx.oxml import OxmlElement
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:cs"), font)
    rFonts.set(qn("w:hAnsi"), font)


def contract_to_docx(contract: DraftedContract) -> bytes:
    """Render the contract to a .docx byte stream."""
    doc = Document()

    # Set whole section to RTL
    section = doc.sections[0]
    sectPr = section._sectPr
    from docx.oxml import OxmlElement
    bidi = OxmlElement("w:bidi")
    sectPr.append(bidi)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    _add_arabic_paragraph(doc, contract.title, bold=True, size=18, align_center=True)
    doc.add_paragraph()

    if contract.preamble:
        _add_arabic_paragraph(doc, contract.preamble, size=12)
        doc.add_paragraph()

    _add_arabic_paragraph(doc, "الأطراف:", bold=True, size=14)
    for i, party in enumerate(contract.parties, start=1):
        line = f"الطرف {_arabic_ordinal(i)}: {party.name}"
        if party.role:
            line += f" ({party.role})"
        if party.address:
            line += f" - يقيم في: {party.address}"
        if party.national_id:
            line += f" - رقم قومي/سجل: {party.national_id}"
        _add_arabic_paragraph(doc, line, size=12)
    doc.add_paragraph()

    if contract.recitals:
        _add_arabic_paragraph(doc, "تمهيد:", bold=True, size=14)
        for r in contract.recitals:
            _add_arabic_paragraph(doc, f"- {r}", size=12)
        doc.add_paragraph()

    if contract.subject:
        _add_arabic_paragraph(doc, "محل العقد:", bold=True, size=14)
        _add_arabic_paragraph(doc, contract.subject, size=12)
        doc.add_paragraph()

    _add_arabic_paragraph(doc, "البنود:", bold=True, size=14)
    for art in contract.articles:
        header = f"البند {_arabic_ordinal(art.number)}: {art.title}"
        _add_arabic_paragraph(doc, header, bold=True, size=13)
        _add_arabic_paragraph(doc, art.body, size=12)
        doc.add_paragraph()

    if contract.governing_law:
        _add_arabic_paragraph(doc, "القانون الحاكم والاختصاص:", bold=True, size=14)
        _add_arabic_paragraph(doc, contract.governing_law, size=12)
        doc.add_paragraph()

    _add_arabic_paragraph(doc, contract.signature_block, size=12)
    doc.add_paragraph()

    # Signature table
    table = doc.add_table(rows=2, cols=len(contract.parties))
    for col, party in enumerate(contract.parties):
        cell = table.cell(0, col)
        cell.text = ""
        p = cell.paragraphs[0]
        _set_rtl(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"الطرف {_arabic_ordinal(col + 1)}\n{party.name}")
        run.bold = True
        run.font.size = Pt(11)

        sig_cell = table.cell(1, col)
        sig_cell.text = ""
        sp = sig_cell.paragraphs[0]
        _set_rtl(sp)
        sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sp.add_run("التوقيع: ____________________").font.size = Pt(11)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _arabic_ordinal(n: int) -> str:
    """Return the Arabic word for the ordinal of n (1..20), else digits."""
    table = {
        1: "الأول", 2: "الثاني", 3: "الثالث", 4: "الرابع", 5: "الخامس",
        6: "السادس", 7: "السابع", 8: "الثامن", 9: "التاسع", 10: "العاشر",
        11: "الحادي عشر", 12: "الثاني عشر", 13: "الثالث عشر", 14: "الرابع عشر",
        15: "الخامس عشر", 16: "السادس عشر", 17: "السابع عشر", 18: "الثامن عشر",
        19: "التاسع عشر", 20: "العشرون",
    }
    return table.get(n, f"رقم {n}")


# ---------------------------------------------------------------------------
# PDF (reportlab + arabic-reshaper + python-bidi)
# ---------------------------------------------------------------------------
def _shape(text: str) -> str:
    """Reshape Arabic for correct cursive joining and reorder for RTL."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


_FONT_CANDIDATES = [
    # (font name, file path)
    ("Arial", "C:/Windows/Fonts/arial.ttf"),
    ("Tahoma", "C:/Windows/Fonts/tahoma.ttf"),
    ("TimesNewRoman", "C:/Windows/Fonts/times.ttf"),
    ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

_REGISTERED_FONT: str | None = None


def _ensure_font() -> str:
    """Register the first Arabic-capable TTF we can find. Cached."""
    global _REGISTERED_FONT
    if _REGISTERED_FONT is not None:
        return _REGISTERED_FONT

    for name, path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _REGISTERED_FONT = name
                return name
            except Exception:
                continue

    # Last resort: reportlab's built-in (no Arabic, but doesn't crash)
    _REGISTERED_FONT = "Helvetica"
    return _REGISTERED_FONT


def contract_to_pdf(contract: DraftedContract) -> bytes:
    """Render the contract to a PDF byte stream."""
    font_name = _ensure_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=contract.title,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        alignment=1,            # center
        wordWrap="RTL",
        leading=24,
    )
    heading_style = ParagraphStyle(
        "ArabicHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        alignment=2,            # right
        wordWrap="RTL",
        leading=20,
        textColor=colors.HexColor("#1f3a8a"),
    )
    body_style = ParagraphStyle(
        "ArabicBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=12,
        alignment=2,            # right
        wordWrap="RTL",
        leading=18,
    )

    story: list = []
    story.append(Paragraph(_shape(contract.title), title_style))
    story.append(Spacer(1, 0.5 * cm))

    if contract.preamble:
        story.append(Paragraph(_shape(contract.preamble), body_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(_shape("الأطراف:"), heading_style))
    for i, p in enumerate(contract.parties, start=1):
        line = f"الطرف {_arabic_ordinal(i)}: {p.name}"
        if p.role:
            line += f" ({p.role})"
        if p.address:
            line += f" - يقيم في: {p.address}"
        if p.national_id:
            line += f" - رقم قومي/سجل: {p.national_id}"
        story.append(Paragraph(_shape(line), body_style))
    story.append(Spacer(1, 0.3 * cm))

    if contract.recitals:
        story.append(Paragraph(_shape("تمهيد:"), heading_style))
        for r in contract.recitals:
            story.append(Paragraph(_shape(f"- {r}"), body_style))
        story.append(Spacer(1, 0.3 * cm))

    if contract.subject:
        story.append(Paragraph(_shape("محل العقد:"), heading_style))
        story.append(Paragraph(_shape(contract.subject), body_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(_shape("البنود:"), heading_style))
    for art in contract.articles:
        story.append(
            Paragraph(
                _shape(f"البند {_arabic_ordinal(art.number)}: {art.title}"),
                heading_style,
            )
        )
        story.append(Paragraph(_shape(art.body), body_style))
        story.append(Spacer(1, 0.2 * cm))

    if contract.governing_law:
        story.append(Paragraph(_shape("القانون الحاكم والاختصاص:"), heading_style))
        story.append(Paragraph(_shape(contract.governing_law), body_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(_shape(contract.signature_block), body_style))
    story.append(Spacer(1, 0.8 * cm))

    # Signature row
    sig_row = [
        Paragraph(
            _shape(f"الطرف {_arabic_ordinal(i + 1)}\n{p.name}\nالتوقيع: __________"),
            body_style,
        )
        for i, p in enumerate(contract.parties)
    ]
    table = Table([sig_row], colWidths=[(17 / max(1, len(sig_row))) * cm] * len(sig_row))
    table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ])
    )
    story.append(table)

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Plain text (for copy/paste)
# ---------------------------------------------------------------------------
def contract_to_text(contract: DraftedContract) -> str:
    lines: list[str] = []
    lines.append(contract.title)
    lines.append("=" * 60)
    if contract.preamble:
        lines.append(contract.preamble)
        lines.append("")
    lines.append("الأطراف:")
    for i, p in enumerate(contract.parties, start=1):
        line = f"  الطرف {_arabic_ordinal(i)}: {p.name}"
        if p.role:
            line += f" ({p.role})"
        if p.address:
            line += f" - {p.address}"
        lines.append(line)
    lines.append("")
    if contract.recitals:
        lines.append("تمهيد:")
        for r in contract.recitals:
            lines.append(f"  - {r}")
        lines.append("")
    if contract.subject:
        lines.append("محل العقد:")
        lines.append(f"  {contract.subject}")
        lines.append("")
    lines.append("البنود:")
    for art in contract.articles:
        lines.append("")
        lines.append(f"البند {_arabic_ordinal(art.number)}: {art.title}")
        lines.append(art.body)
    lines.append("")
    if contract.governing_law:
        lines.append("القانون الحاكم والاختصاص:")
        lines.append(f"  {contract.governing_law}")
        lines.append("")
    lines.append(contract.signature_block)
    lines.append("")
    for i, p in enumerate(contract.parties, start=1):
        lines.append(f"الطرف {_arabic_ordinal(i)} ({p.name}): التوقيع ____________________")
    return "\n".join(lines)
