"""
Document classification for the reviewer console.

WHAT THE MODEL DOES AND DOES NOT DO
-----------------------------------
The model reads a document and proposes a type. That is all. It does not set the
confidence band, and it is never asked how confident it is - a self-reported
percentage is not calibrated and would eventually be quoted in an appeal.

The band is computed here, from signals we can check ourselves:

  alta   two independent views of the document (its first page, and its full
         text) were classified the same way, and the document has real text
  media  only one view was available - a scan classified from its page images,
         or a document whose text is too sparse for a second view
  baja   the two views disagreed, the model returned something outside the
         taxonomy, no evidence could be read at all, or the call failed

A `baja` band never produces a label. The document is recorded as `desconocido`
with a reason, and a human decides. Escalating is always safe; guessing is not.

Anthropic only - the applicant flow's OpenAI calls are untouched and no OpenAI
client is imported anywhere in this package.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from app.config import get_settings
from app.reviewer import taxonomy
from app.reviewer.pdf_text import PdfAnalysis, first_pages_pdf

logger = logging.getLogger(__name__)

# Enough for a type code, a page number, and a one-line rationale.
_MAX_TOKENS = 1500

# How many opening pages of a scanned document go to the model.
_SCAN_PAGE_LIMIT = 4

_SYSTEM_PROMPT = (
    "Eres un asistente de una oficina municipal de permisos en Puerto Rico. "
    "Clasificas documentos que forman parte de una solicitud de Permiso Unico.\n\n"
    "Reglas:\n"
    "1. Devuelve el codigo exacto del catalogo. Si el documento no corresponde "
    "claramente a ninguna categoria, devuelve 'desconocido'.\n"
    "2. NUNCA adivines. 'desconocido' es una respuesta correcta y esperada.\n"
    "3. Indica el numero de pagina donde viste la evidencia que sustenta tu "
    "clasificacion. Si no puedes identificar una pagina, usa 0.\n"
    "4. La razon debe citar lo que viste en el documento, no una suposicion."
)

_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {
            "type": "string",
            "description": "Codigo del catalogo, o 'desconocido'.",
        },
        "evidence_page": {
            "type": "integer",
            "description": "Pagina (1-indexada) donde aparece la evidencia; 0 si ninguna.",
        },
        "evidence_quote": {
            "type": "string",
            "description": "Texto breve del documento que sustenta la clasificacion.",
        },
    },
    "required": ["doc_type", "evidence_page", "evidence_quote"],
    "additionalProperties": False,
}


@dataclass
class Classification:
    doc_type: str
    band: str            # 'alta' | 'media' | 'baja'
    reason: str          # machine-generated, names the specific trigger
    evidence_page: Optional[int]
    ok: bool = True      # False when the call itself failed


def _client():
    """Create the Anthropic client, or None when no key is configured."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:  # pragma: no cover - dependency is declared in requirements
        logger.error("anthropic package is not installed")
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _ask(client, model: str, content) -> Optional[dict]:
    """One classification call. Returns the parsed object, or None on failure."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            output_config={
                "format": {"type": "json_schema", "schema": _RESULT_SCHEMA},
                "effort": "medium",
            },
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        logger.warning("Anthropic classification call failed: %s", exc)
        return None

    if getattr(response, "stop_reason", None) == "refusal":
        logger.warning("Classification refused by safety classifier")
        return None

    try:
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)
    except (StopIteration, json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Could not read classification response: %s", exc)
        return None


def _normalize(raw: Optional[dict]) -> Tuple[Optional[str], Optional[int], str]:
    """
    Pull a valid type code, page, and quote out of a model response.

    A code outside the taxonomy is discarded rather than trusted - the catalog is
    the authority, not the model.
    """
    if not raw:
        return None, None, ""

    code = (raw.get("doc_type") or "").strip()
    if code not in taxonomy.valid_codes():
        logger.info("Model returned an out-of-catalog code: %r", code)
        return None, None, ""

    page = raw.get("evidence_page")
    page = int(page) if isinstance(page, int) and page > 0 else None

    return code, page, (raw.get("evidence_quote") or "").strip()[:500]


def _text_prompt(view_label: str, body: str) -> str:
    return (
        f"CATALOGO DE DOCUMENTOS DEL PERMISO UNICO:\n{taxonomy.catalog_for_prompt()}\n\n"
        f"VISTA DEL DOCUMENTO ({view_label}):\n{body}\n\n"
        "Clasifica este documento."
    )


def classify(
    analysis: PdfAnalysis,
    filename: str,
    pdf_bytes: bytes,
) -> Classification:
    """
    Classify one document and derive its band.

    Never raises: a failure becomes `desconocido` / `baja` with a reason, because
    one unclassifiable file must not take down a five-file upload.
    """
    client = _client()
    if client is None:
        return Classification(
            doc_type=taxonomy.UNKNOWN,
            band="baja",
            reason="clasificador_no_configurado: falta ANTHROPIC_API_KEY",
            evidence_page=None,
            ok=False,
        )

    model = get_settings().reviewer_model

    # ---- Case 1: nothing readable at all -------------------------------------
    if analysis.ocr_status == "error":
        return Classification(
            doc_type=taxonomy.UNKNOWN,
            band="baja",
            reason=f"evidencia_no_disponible: {analysis.error or 'el PDF no se pudo leer'}",
            evidence_page=None,
            ok=False,
        )

    # ---- Case 2: a scan - one view only, so the band tops out at 'media' -----
    if not analysis.readable:
        excerpt = first_pages_pdf(pdf_bytes, _SCAN_PAGE_LIMIT)
        if excerpt is None:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="evidencia_no_disponible: documento sin texto y no se pudo preparar para lectura visual",
                evidence_page=None,
                ok=False,
            )

        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(excerpt).decode("ascii"),
                },
            },
            {
                "type": "text",
                "text": _text_prompt(
                    f"documento escaneado, primeras {_SCAN_PAGE_LIMIT} paginas, archivo '{filename}'",
                    "(sin texto incrustado; lee las imagenes)",
                ),
            },
        ]

        code, page, _quote = _normalize(_ask(client, model, content))

        if code is None:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="clasificacion_fallida: no se obtuvo un codigo valido del documento escaneado",
                evidence_page=None,
                ok=False,
            )
        if code == taxonomy.UNKNOWN:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="sin_coincidencia: el documento escaneado no corresponde a una categoria del catalogo",
                evidence_page=page,
            )

        return Classification(
            doc_type=code,
            band="media",
            reason=(
                "pase_unico: documento sin texto incrustado, clasificado a partir de "
                f"las primeras {_SCAN_PAGE_LIMIT} paginas escaneadas"
            ),
            evidence_page=page,
        )

    # ---- Case 3: text-bearing - two independent views -------------------------
    first_view = analysis.first_page_text()
    full_view = analysis.combined_text()

    code_a, page_a, _ = _normalize(
        _ask(client, model, _text_prompt(f"primera pagina con texto, archivo '{filename}'", first_view))
    )

    # A very short document has no meaningful second view; treat it as one pass
    # rather than pretending two identical reads agree.
    single_view = full_view.strip() == first_view.strip()

    if single_view:
        if code_a is None:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="clasificacion_fallida: no se obtuvo un codigo valido",
                evidence_page=None,
                ok=False,
            )
        if code_a == taxonomy.UNKNOWN:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="sin_coincidencia: no corresponde a una categoria del catalogo",
                evidence_page=page_a,
            )
        return Classification(
            doc_type=code_a,
            band="media",
            reason="pase_unico: el documento es demasiado corto para una segunda vista independiente",
            evidence_page=page_a or analysis.first_text_page_no(),
        )

    code_b, page_b, _ = _normalize(
        _ask(client, model, _text_prompt(f"texto completo, archivo '{filename}'", full_view))
    )

    if code_a is None or code_b is None:
        available = code_a or code_b
        if available is None:
            return Classification(
                doc_type=taxonomy.UNKNOWN,
                band="baja",
                reason="clasificacion_fallida: ninguna de las dos vistas produjo un codigo valido",
                evidence_page=None,
                ok=False,
            )
        return Classification(
            doc_type=taxonomy.UNKNOWN,
            band="baja",
            reason="pase_incompleto: solo una de las dos vistas produjo un codigo valido",
            evidence_page=page_a or page_b,
        )

    if code_a != code_b:
        return Classification(
            doc_type=taxonomy.UNKNOWN,
            band="baja",
            reason=(
                "vistas_contradictorias: la primera pagina sugiere "
                f"'{taxonomy.label_for(code_a)}' y el texto completo sugiere "
                f"'{taxonomy.label_for(code_b)}'"
            ),
            evidence_page=page_a or page_b,
        )

    if code_a == taxonomy.UNKNOWN:
        return Classification(
            doc_type=taxonomy.UNKNOWN,
            band="baja",
            reason="sin_coincidencia: ambas vistas coinciden en que no corresponde al catalogo",
            evidence_page=None,
        )

    # Both views agree on a real type.
    band = "alta" if analysis.ocr_status == "texto_incrustado" else "media"
    reason = (
        "concordancia: ambas vistas coinciden y el documento tiene texto incrustado"
        if band == "alta"
        else "concordancia_parcial: ambas vistas coinciden, pero solo parte del documento tiene texto"
    )

    return Classification(
        doc_type=code_a,
        band=band,
        reason=reason,
        evidence_page=page_a or page_b or analysis.first_text_page_no(),
    )
