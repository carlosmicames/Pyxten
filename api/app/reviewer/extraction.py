"""
Pulling facts out of a document, with provenance.

The model reads. It does not decide anything: it proposes a value, a page and a
quote, and this module decides whether that reading is usable and how confident
the system is entitled to be about it.

INDEPENDENCE COMES FROM A SECOND VIEW, NOT A SECOND VENDOR
Each field is read twice from genuinely different material - once from the text
layer, once from the page images - and the two readings are compared here. Two
modalities have different failure modes, which is what makes agreement mean
something. Routing the same document to a second AI vendor would add a
subprocessor to a government deployment without adding independence: two models
agreeing makes a value popular, not true.

BANDS ARE DERIVED, NEVER ASKED FOR
  alta   both views found the field and agree after normalization
  media  only one view found it - a scan with no text layer, or a field the
         other modality could not see
  baja   the views disagree, or nothing was found

A value with no page number is not a fact. It is recorded as
evidencia_no_disponible, because a finding that cannot point at a page cannot be
defended in an appeal.

Anthropic only.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.reviewer.pdf_text import PdfAnalysis, first_pages_pdf
from app.reviewer.rules.normalize import basic, norm_catastro, norm_date

logger = logging.getLogger(__name__)

_MAX_TOKENS = 4000

# The image view is expensive and the identifying content of a permit document
# is at the front. Reading the whole of a 200-page package twice is not worth it.
_IMAGE_VIEW_PAGES = 8

# How much text goes to the text view.
_TEXT_VIEW_CHARS = 60_000


@dataclass(frozen=True)
class FieldSpec:
    key: str        # short key; the full fact key is "<doc_type>.<key>"
    label: str      # what to call it in the prompt
    kind: str       # 'text' | 'date' | 'catastro'
    hint: str       # where on the document it usually appears


# =============================================================================
# The extraction contract
#
# These keys are exactly what the seeded rules reference. A test asserts that
# every `<doc_type>.<field>` appearing in migration 007 has a spec here, so
# adding a rule that reads a new field fails the build until extraction knows
# how to find it.
# =============================================================================

FIELD_SPECS: Dict[str, List[FieldSpec]] = {
    "registro_comerciante": [
        FieldSpec("nombre_solicitante", "Nombre del comerciante o entidad", "text",
                  "Titular del registro"),
        FieldSpec("nombre_comercial", "Nombre comercial (DBA)", "text",
                  "Nombre bajo el cual opera el negocio"),
        FieldSpec("actividad", "Actividad o naturaleza del negocio", "text",
                  "Descripcion de la actividad comercial"),
        FieldSpec("estatus", "Estatus del registro", "text",
                  "Activo, inactivo, revocado, cancelado o suspendido"),
    ],
    "patente_municipal": [
        FieldSpec("nombre_solicitante", "Nombre del solicitante o entidad", "text",
                  "A nombre de quien se expide la patente"),
        FieldSpec("nombre_comercial", "Nombre comercial", "text", "Nombre del negocio"),
        FieldSpec("actividad", "Actividad comercial autorizada", "text", None or ""),
        FieldSpec("periodo_hasta", "Fecha final del periodo cubierto", "date",
                  "Vigencia de la patente; el fin del semestre o ano fiscal"),
        FieldSpec("direccion_negocio", "Direccion fisica del negocio", "text",
                  "Local donde opera, no la direccion postal"),
    ],
    "certificacion_crim": [
        FieldSpec("nombre_solicitante", "Nombre del contribuyente", "text", ""),
        FieldSpec("catastro", "Numero de catastro", "catastro",
                  "Identificador de la propiedad, normalmente con guiones"),
        FieldSpec("fecha_vencimiento", "Fecha de vencimiento o validez", "date",
                  "Hasta cuando es valida la certificacion"),
        FieldSpec("entidad_emisora", "Entidad que emite el documento", "text",
                  "Nombre del organismo en el membrete o la firma"),
    ],
    "certificacion_asume": [
        FieldSpec("nombre_solicitante", "Nombre de la persona certificada", "text", ""),
        FieldSpec("fecha_vencimiento", "Fecha de vencimiento o validez", "date", ""),
        FieldSpec("entidad_emisora", "Entidad que emite el documento", "text", ""),
    ],
    "certificado_bomberos": [
        FieldSpec("direccion_negocio", "Direccion del local inspeccionado", "text", ""),
        FieldSpec("fecha_vencimiento", "Fecha de vencimiento del certificado", "date", ""),
        FieldSpec("entidad_emisora", "Entidad que emite el certificado", "text", ""),
    ],
    "certificado_salud": [
        FieldSpec("fecha_vencimiento", "Fecha de vencimiento del certificado", "date", ""),
        FieldSpec("entidad_emisora", "Entidad que emite el certificado", "text", ""),
    ],
    "contrato_arrendamiento": [
        FieldSpec("arrendador", "Nombre del arrendador", "text", "Quien cede el local"),
        FieldSpec("arrendatario", "Nombre del arrendatario", "text", "Quien lo toma"),
        FieldSpec("vigencia_hasta", "Fecha en que termina el contrato", "date", ""),
    ],
    "escritura_titularidad": [
        FieldSpec("titular", "Nombre del titular de la propiedad", "text",
                  "Quien adquiere en la escritura"),
        FieldSpec("catastro", "Numero de catastro", "catastro", ""),
    ],
    "plano_distribucion": [
        FieldSpec("profesional_autorizado", "Profesional que firma el plano", "text",
                  "Arquitecto o ingeniero, normalmente en el sello"),
        FieldSpec("numero_licencia", "Numero de licencia o colegiado", "text", ""),
    ],
}


@dataclass
class ExtractedFact:
    field_key: str                   # "<doc_type>.<field>"
    value_text: Optional[str]
    value_date: Optional[str]        # ISO string, or None
    source_page: Optional[int]
    band: str                        # alta | media | baja
    status: str                      # extraido | evidencia_no_disponible | contradictorio
    quote: Optional[str] = None
    note: Optional[str] = None

    def as_row(self, case_id: str, org_id: str, document_id: str) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "org_id": org_id,
            "document_id": document_id,
            "field_key": self.field_key,
            "value_text": self.value_text,
            "value_date": self.value_date,
            "source_page": self.source_page,
            "band": self.band,
            "status": self.status,
        }


# =============================================================================
# Model access
# =============================================================================

def _client():
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        logger.error("anthropic package is not installed")
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


_SYSTEM_PROMPT = (
    "Extraes datos de documentos de una solicitud de Permiso Unico en Puerto Rico "
    "para una oficina municipal de permisos.\n\n"
    "Reglas:\n"
    "1. Transcribe el valor EXACTAMENTE como aparece en el documento. No lo "
    "corrijas, no lo completes y no lo traduzcas.\n"
    "2. Indica la pagina donde lo viste. Si no puedes identificar la pagina, "
    "marca el campo como no encontrado.\n"
    "3. Si un campo no aparece en el documento, marca encontrado=false y deja el "
    "valor vacio. NUNCA inventes ni deduzcas un valor.\n"
    "4. Incluye una cita breve del texto donde aparece el dato."
)


def _schema(specs: List[FieldSpec]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "campos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "campo": {"type": "string", "enum": [s.key for s in specs]},
                        "encontrado": {"type": "boolean"},
                        "valor": {"type": "string"},
                        "pagina": {"type": "integer"},
                        "cita": {"type": "string"},
                    },
                    "required": ["campo", "encontrado", "valor", "pagina", "cita"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["campos"],
        "additionalProperties": False,
    }


def _field_list(specs: List[FieldSpec]) -> str:
    lines = []
    for spec in specs:
        kind = {"date": "fecha", "catastro": "numero de catastro"}.get(spec.kind, "texto")
        hint = f" ({spec.hint})" if spec.hint else ""
        lines.append(f"- {spec.key}: {spec.label}{hint}. Tipo: {kind}.")
    return "\n".join(lines)


def _ask(client, model: str, content, specs: List[FieldSpec]) -> Optional[Dict[str, Any]]:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            output_config={
                "format": {"type": "json_schema", "schema": _schema(specs)},
                "effort": "medium",
            },
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        logger.warning("Extraction call failed: %s", exc)
        return None

    if getattr(response, "stop_reason", None) == "refusal":
        logger.warning("Extraction refused by safety classifier")
        return None

    try:
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)
    except (StopIteration, json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Could not read extraction response: %s", exc)
        return None


def _readings(raw: Optional[Dict[str, Any]], specs: List[FieldSpec]) -> Dict[str, Dict[str, Any]]:
    """
    One view's answers, keyed by field.

    A field with no page is dropped: an unciteable value is not evidence, and
    keeping it would let it agree with the other view and reach a high band.
    """
    valid = {s.key for s in specs}
    out: Dict[str, Dict[str, Any]] = {}

    for entry in (raw or {}).get("campos", []) or []:
        key = entry.get("campo")
        if key not in valid or not entry.get("encontrado"):
            continue

        value = (entry.get("valor") or "").strip()
        page = entry.get("pagina")
        if not value or not isinstance(page, int) or page < 1:
            continue

        out[key] = {"value": value, "page": page, "quote": (entry.get("cita") or "").strip()[:400]}

    return out


# =============================================================================
# Comparison
# =============================================================================

def _canonical(value: str, kind: str) -> str:
    if kind == "date":
        parsed = norm_date(value)
        return parsed.isoformat() if parsed else basic(value)
    if kind == "catastro":
        return norm_catastro(value)
    return basic(value)


def _reconcile(
    spec: FieldSpec,
    doc_type: str,
    text_view: Optional[Dict[str, Any]],
    image_view: Optional[Dict[str, Any]],
    single_view: bool,
) -> ExtractedFact:
    """
    Turn two readings of one field into a fact with a band, deterministically.
    """
    field_key = f"{doc_type}.{spec.key}"

    def build(reading, band, status, note=None):
        value = reading["value"]
        parsed = norm_date(value) if spec.kind == "date" else None
        return ExtractedFact(
            field_key=field_key,
            value_text=value,
            value_date=parsed.isoformat() if parsed else None,
            source_page=reading["page"],
            band=band,
            status=status,
            quote=reading.get("quote"),
            note=note,
        )

    def unavailable(note):
        return ExtractedFact(
            field_key=field_key,
            value_text=None,
            value_date=None,
            source_page=None,
            band="baja",
            status="evidencia_no_disponible",
            note=note,
        )

    if text_view and image_view:
        if _canonical(text_view["value"], spec.kind) == _canonical(image_view["value"], spec.kind):
            # Two modalities, same answer. This is the only route to `alta`.
            return build(text_view, "alta", "extraido", "concordancia_entre_vistas")

        # They disagree. Record it as contradictory with both readings noted;
        # the rule that reads this field will escalate.
        fact = build(text_view, "baja", "contradictorio", "vistas_contradictorias")
        fact.note = (
            f"vistas_contradictorias: texto='{text_view['value']}' "
            f"(p. {text_view['page']}) imagen='{image_view['value']}' (p. {image_view['page']})"
        )
        return fact

    if text_view:
        return build(
            text_view, "media", "extraido",
            "vista_unica" if single_view else "solo_vista_texto",
        )

    if image_view:
        return build(image_view, "media", "extraido", "solo_vista_imagen")

    return unavailable("no_localizado_en_ninguna_vista")


# =============================================================================
# Entry point
# =============================================================================

def extract_document(
    analysis: PdfAnalysis,
    pdf_bytes: bytes,
    doc_type: str,
) -> Tuple[List[ExtractedFact], Optional[str]]:
    """
    Extract every field this document type is expected to carry.

    Returns (facts, error). Never raises: a document that cannot be read yields
    evidencia_no_disponible facts, which is a valid state that escalates the
    rules depending on them rather than losing them.
    """
    specs = FIELD_SPECS.get(doc_type)
    if not specs:
        # Nothing is extracted from a type no rule reads, including desconocido.
        return [], None

    client = _client()
    if client is None:
        return (
            [_reconcile(s, doc_type, None, None, True) for s in specs],
            "extractor_no_configurado: falta ANTHROPIC_API_KEY",
        )

    model = get_settings().reviewer_model
    prompt_fields = _field_list(specs)

    # --- View 1: the text layer ----------------------------------------------
    text_readings: Dict[str, Dict[str, Any]] = {}
    if analysis.readable:
        body = analysis.combined_text(_TEXT_VIEW_CHARS)
        text_readings = _readings(
            _ask(
                client, model,
                (
                    f"TIPO DE DOCUMENTO: {doc_type}\n\n"
                    f"CAMPOS A EXTRAER:\n{prompt_fields}\n\n"
                    f"TEXTO DEL DOCUMENTO (delimitado por pagina):\n{body}"
                ),
                specs,
            ),
            specs,
        )

    # --- View 2: the page images ---------------------------------------------
    # Genuinely different material, not a re-run: a value the text layer
    # mangled and one the rendering makes plain fail in different ways.
    image_readings: Dict[str, Dict[str, Any]] = {}
    excerpt = first_pages_pdf(pdf_bytes, _IMAGE_VIEW_PAGES)
    if excerpt is not None:
        image_readings = _readings(
            _ask(
                client, model,
                [
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
                        "text": (
                            f"TIPO DE DOCUMENTO: {doc_type}\n\n"
                            f"CAMPOS A EXTRAER:\n{prompt_fields}\n\n"
                            "Lee el documento adjunto. Las paginas estan numeradas "
                            "desde 1 en el orden en que aparecen."
                        ),
                    },
                ],
                specs,
            ),
            specs,
        )

    single_view = not analysis.readable or excerpt is None

    facts = [
        _reconcile(spec, doc_type, text_readings.get(spec.key), image_readings.get(spec.key), single_view)
        for spec in specs
    ]

    return facts, None


def expected_field_keys() -> set:
    """Every fact key extraction can produce. Used to check the rules line up."""
    return {
        f"{doc_type}.{spec.key}"
        for doc_type, specs in FIELD_SPECS.items()
        for spec in specs
    }
