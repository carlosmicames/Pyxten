"""
Rendering the requerimiento to PDF.

Two things this does that the existing generators do not.

ACCENTS
The applicant-side PDFs write unaccented Spanish throughout ("Direccion",
"Validacion") to avoid font encoding problems. A document a municipality signs
and serves cannot do that. Bitstream Vera ships inside the reportlab package
itself, so it is present wherever reportlab is, and it carries the full Latin-1
range: acentos, enye, and the inverted marks.

BORRADOR
A draft is watermarked on every page and says so in its title. The watermark is
removed only when the notice has been approved by a person - which is a database
state, not a render option a caller can pass.
"""
from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

BODY_FONT = "Vera"
BOLD_FONT = "Vera-Bold"
_FONTS_REGISTERED = False


def _register_fonts() -> bool:
    """
    Register a Unicode font. Returns False if it could not be found, in which
    case the caller falls back to Helvetica and the document loses its accents -
    degraded, but still produced.
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return True

    try:
        import reportlab

        fonts_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
        pdfmetrics.registerFont(TTFont(BODY_FONT, os.path.join(fonts_dir, "Vera.ttf")))
        pdfmetrics.registerFont(TTFont(BOLD_FONT, os.path.join(fonts_dir, "VeraBd.ttf")))
        _FONTS_REGISTERED = True
        return True
    except Exception as exc:
        logger.error("Could not register a Unicode font: %s", exc)
        return False


def _styles(unicode_ok: bool):
    body = BODY_FONT if unicode_ok else "Helvetica"
    bold = BOLD_FONT if unicode_ok else "Helvetica-Bold"

    sheet = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "ReqTitulo", parent=sheet["Title"], fontName=bold, fontSize=15,
            leading=19, spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "ReqSubtitulo", parent=sheet["Normal"], fontName=body, fontSize=10,
            leading=13, textColor=colors.HexColor("#444444"), spaceAfter=14,
        ),
        "seccion": ParagraphStyle(
            "ReqSeccion", parent=sheet["Heading2"], fontName=bold, fontSize=11,
            leading=14, spaceBefore=14, spaceAfter=6,
        ),
        "cuerpo": ParagraphStyle(
            "ReqCuerpo", parent=sheet["Normal"], fontName=body, fontSize=10,
            leading=14.5, alignment=TA_JUSTIFY, spaceAfter=8,
        ),
        "hallazgo": ParagraphStyle(
            "ReqHallazgo", parent=sheet["Normal"], fontName=bold, fontSize=10.5,
            leading=14, spaceBefore=10, spaceAfter=4,
        ),
        "evidencia": ParagraphStyle(
            "ReqEvidencia", parent=sheet["Normal"], fontName=body, fontSize=8.5,
            leading=11.5, textColor=colors.HexColor("#555555"), leftIndent=12,
            spaceAfter=2,
        ),
        "nota": ParagraphStyle(
            "ReqNota", parent=sheet["Normal"], fontName=body, fontSize=8.5,
            leading=11.5, textColor=colors.HexColor("#666666"), spaceBefore=10,
        ),
    }


def _escape(value: Any) -> str:
    """Paragraph text is XML-ish; user and model text must not be able to break it."""
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _watermark(canvas, doc):
    """BORRADOR across every page, plus a page number."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 68)
    canvas.setFillColor(colors.Color(0.85, 0.15, 0.1, alpha=0.10))
    canvas.translate(letter[0] / 2, letter[1] / 2)
    canvas.rotate(38)
    canvas.drawCentredString(0, 0, "BORRADOR")
    canvas.restoreState()
    _page_number(canvas, doc)


def _page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawCentredString(letter[0] / 2, 0.55 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def render(requerimiento: Dict[str, Any]) -> bytes:
    """Render one notice. `status` decides whether it carries the draft watermark."""
    unicode_ok = _register_fonts()
    style = _styles(unicode_ok)

    body = requerimiento.get("body") or {}
    header = body.get("encabezado") or {}
    is_draft = requerimiento.get("status") != "aprobado"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title=f"Requerimiento de subsanacion - {header.get('case_number', '')}",
    )

    story = []

    # ---- Heading -------------------------------------------------------------
    story.append(Paragraph(_escape(header.get("oficina") or "Oficina de Permisos"), style["titulo"]))
    story.append(
        Paragraph(
            f"Municipio de {_escape(header.get('municipio'))} · "
            f"Requerimiento de subsanación",
            style["subtitulo"],
        )
    )

    facts = [
        ["Expediente:", header.get("case_number") or "—"],
        ["Solicitante:", header.get("solicitante") or "No indicado"],
        ["Dirección:", header.get("direccion") or "No indicada"],
        ["Catastro:", header.get("catastro") or "No indicado"],
        ["Fecha:", header.get("fecha") or "—"],
    ]
    table = Table(
        [[Paragraph(f"<b>{_escape(k)}</b>", style["cuerpo"]), Paragraph(_escape(v), style["cuerpo"])]
         for k, v in facts],
        colWidths=[1.35 * inch, 4.9 * inch],
    )
    table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 14))

    # ---- Introduction --------------------------------------------------------
    story.append(Paragraph(_escape(body.get("introduccion")), style["cuerpo"]))

    # ---- Findings ------------------------------------------------------------
    hallazgos = body.get("hallazgos") or []
    story.append(
        Paragraph(
            f"Señalamientos identificados ({len(hallazgos)})", style["seccion"]
        )
    )

    for item in hallazgos:
        block = [
            Paragraph(
                f"{item.get('numero')}. {_escape(item.get('titulo'))}", style["hallazgo"]
            ),
            Paragraph(_escape(item.get("parrafo")), style["cuerpo"]),
        ]
        if item.get("subsanacion"):
            block.append(
                Paragraph(
                    f"<b>Subsanación requerida:</b> {_escape(item['subsanacion'])}",
                    style["cuerpo"],
                )
            )

        # Evidence is appended by the system, not written by the model.
        for evidence in item.get("evidencia") or []:
            reference = f"{_escape(evidence.get('documento'))}, pág. {evidence.get('pagina')}"
            if evidence.get("valor"):
                reference += f" — “{_escape(evidence['valor'])}”"
            block.append(Paragraph(f"Evidencia: {reference}", style["evidencia"]))

        if item.get("fundamento"):
            block.append(
                Paragraph(f"Fundamento: {_escape(item['fundamento'])}", style["evidencia"])
            )

        story.append(KeepTogether(block))

    # ---- Closing -------------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph(_escape(body.get("cierre")), style["cuerpo"]))

    # ---- What this document does not cover -----------------------------------
    pending = body.get("pendientes_de_criterio") or []
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Este documento recoge únicamente los señalamientos identificados en las "
            "verificaciones cubiertas por esta revisión. No constituye una "
            "determinación sobre el cumplimiento total de la solicitud."
            + (
                f" Quedan {len(pending)} verificaciones pendientes de criterio del "
                "revisor que no se incluyen en este requerimiento."
                if pending
                else ""
            ),
            style["nota"],
        )
    )

    if is_draft:
        story.append(
            Paragraph(
                "BORRADOR — documento no aprobado. Requiere revisión y aprobación "
                "antes de ser notificado al solicitante.",
                style["nota"],
            )
        )

    doc.build(
        story,
        onFirstPage=_watermark if is_draft else _page_number,
        onLaterPages=_watermark if is_draft else _page_number,
    )

    return buffer.getvalue()
