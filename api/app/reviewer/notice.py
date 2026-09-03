"""
Drafting the requerimiento de subsanacion.

This is the deliverable. Everything else in the reviewer console exists to feed
it, and the whole design turns on one boundary:

    THE MODEL RECEIVES DECIDED FINDINGS. IT WRITES PROSE AROUND THEM.

It is never shown the raw extraction, the facts, or the documents. It has no
capacity to add a deficiency, drop one, or change what one says - the list is
fixed before the call and reconciled after it. A paragraph that cites a page the
finding does not have is discarded and replaced with a deterministic one.

The notice fails closed in every direction:
  * only `hallazgo_identificado` checks go in - a check the system could not
    determine is not a deficiency to serve on an applicant
  * a case with no findings produces no notice at all
  * an API failure still produces a complete document, from the engine's own
    explanations
  * nothing here sends anything; approval is a separate, recorded act

Anthropic only.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.reviewer import audit, taxonomy
from app.reviewer.context import ReviewerContext

logger = logging.getLogger(__name__)

REQUERIMIENTO_DRAFTED = "requerimiento_drafted"
REQUERIMIENTO_APPROVED = "requerimiento_approved"
REQUERIMIENTO_DISCARDED = "requerimiento_discarded"

FINDING = "hallazgo_identificado"
NEEDS_REVIEW = "requiere_criterio"

_MAX_TOKENS = 8000

# A page reference the model wrote, in the forms a Spanish notice uses.
_PAGE_REFERENCE = re.compile(r"\b(?:p[áa]g(?:ina)?\.?|p\.)\s*(\d{1,4})", re.IGNORECASE)

# Anything that looks like a confidence percentage.
_PERCENTAGE = re.compile(r"\b\d{1,3}\s?%")

# Words that must never reach a generated document.
_FORBIDDEN = ("COMPLIANT", "NON-COMPLIANT")


@dataclass
class Finding:
    """One decided deficiency, with everything the notice may say about it."""
    check_id: str
    rule_code: str
    title: str
    citation: Optional[str]
    severity: str
    explanation: str
    evidence: List[Dict[str, Any]]

    @property
    def pages(self) -> set:
        return {e["pagina"] for e in self.evidence if e.get("pagina")}


# =============================================================================
# Selecting what goes in
# =============================================================================

def collect(
    ctx: ReviewerContext,
    case_id: str,
    ruleset_id: Optional[str] = None,
) -> Tuple[List[Finding], List[Dict[str, Any]]]:
    """
    The findings a notice may rest on, and the checks still awaiting a person.

    Only `hallazgo_identificado` is eligible. A `requiere_criterio` check is the
    system saying it could not determine something - serving that on an
    applicant as a deficiency would be asserting what we do not know.
    """
    rows = ctx.db.select(
        "compliance_checks",
        columns=(
            "id,rule_id,family,status,band,evidence_ids,citations,explanation,"
            "reason_code,evaluated_at,rules(code,title,citation,severity)"
        ),
        filters={"case_id": f"eq.{case_id}"},
        order="evaluated_at.desc",
    )

    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        latest.setdefault(row["rule_id"], row)

    documents = ctx.db.select(
        "case_documents",
        columns="id,filename,doc_type",
        filters={"case_id": f"eq.{case_id}"},
    )
    doc_types = taxonomy.types_for_ruleset(ctx, ruleset_id)
    doc_label = {
        d["id"]: taxonomy.label_for(d.get("doc_type"), doc_types) or d.get("filename")
        for d in documents
    }

    findings: List[Finding] = []
    pending: List[Dict[str, Any]] = []

    for row in latest.values():
        rule = row.get("rules") or {}

        if row["status"] == NEEDS_REVIEW:
            pending.append(
                {
                    "rule_code": rule.get("code"),
                    "title": rule.get("title"),
                    "reason_code": row.get("reason_code"),
                }
            )
            continue

        if row["status"] != FINDING:
            continue

        evidence = [
            {
                "documento": doc_label.get(c["document_id"], "Documento"),
                "document_id": c["document_id"],
                "pagina": c.get("page"),
                "valor": c.get("value"),
            }
            for c in (row.get("citations") or [])
            if c.get("document_id")
        ]

        findings.append(
            Finding(
                check_id=row["id"],
                rule_code=rule.get("code") or "",
                title=rule.get("title") or "",
                citation=rule.get("citation"),
                severity=rule.get("severity") or "moderada",
                explanation=row.get("explanation") or "",
                evidence=evidence,
            )
        )

    # Gravest first, then by rule code, so the notice leads with what matters.
    weight = {"grave": 0, "moderada": 1, "leve": 2}
    findings.sort(key=lambda f: (weight.get(f.severity, 3), f.rule_code))

    return findings, pending


# =============================================================================
# Prose
# =============================================================================

def _client():
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


_SYSTEM_PROMPT = (
    "Redactas requerimientos de subsanacion para una oficina municipal de "
    "permisos en Puerto Rico. Escribes en espanol formal administrativo, "
    "dirigiendote al solicitante de usted.\n\n"
    "Reglas estrictas:\n"
    "1. Redactas UNICAMENTE sobre los hallazgos que se te entregan. No anadas, "
    "no elimines y no combines hallazgos.\n"
    "2. No inventes hechos, fechas, numeros ni nombres. Si un dato no aparece en "
    "el hallazgo, no lo menciones.\n"
    "3. NO escribas numeros de pagina ni nombres de documentos: el sistema "
    "anade la referencia de evidencia despues de tu texto.\n"
    "4. No uses porcentajes ni expreses grados de certeza.\n"
    "5. Para cada hallazgo escribe dos cosas: que se identifico, y que debe "
    "presentar o corregir el solicitante para subsanarlo.\n"
    "6. Tono neutral y profesional. No acuses ni supongas mala fe."
)


def _schema(codes: List[str]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "introduccion": {"type": "string"},
            "cierre": {"type": "string"},
            "hallazgos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule_code": {"type": "string", "enum": codes},
                        "parrafo": {"type": "string"},
                        "subsanacion": {"type": "string"},
                    },
                    "required": ["rule_code", "parrafo", "subsanacion"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["introduccion", "cierre", "hallazgos"],
        "additionalProperties": False,
    }


def _prompt(findings: List[Finding], case: Dict[str, Any], municipality: str) -> str:
    lines = [
        f"MUNICIPIO: {municipality}",
        f"EXPEDIENTE: {case.get('case_number')}",
        f"SOLICITANTE: {case.get('applicant_name') or 'No indicado'}",
        "",
        "HALLAZGOS IDENTIFICADOS (redacta uno por cada uno, sin anadir otros):",
    ]
    for index, finding in enumerate(findings, start=1):
        lines.append(f"\n{index}. [{finding.rule_code}] {finding.title}")
        lines.append(f"   Determinacion del sistema: {finding.explanation}")
        if finding.citation:
            lines.append(f"   Fundamento: {finding.citation}")
    return "\n".join(lines)


def _fallback(finding: Finding) -> Dict[str, str]:
    """
    A deterministic paragraph, used when the model is unavailable or its text
    fails validation. The notice is always producible: an API outage must not
    stop a municipal office issuing a requerimiento.
    """
    return {
        "parrafo": (
            f"Se identifico lo siguiente en relacion con: {finding.title}. "
            f"{finding.explanation}"
        ),
        "subsanacion": (
            "El solicitante debera presentar la documentacion o correccion que "
            "atienda este senalamiento."
        ),
        "generado": "sistema",
    }


def _validate(text: str, finding: Finding) -> Optional[str]:
    """
    Reject prose that a signed notice must not carry. Returns a reason, or None.

    The page check is the important one: the model is told not to write page
    numbers, but if it does anyway, every one it writes has to correspond to a
    page this finding actually cites. Anything else is a fabricated reference.
    """
    upper = text.upper()
    for word in _FORBIDDEN:
        if word in upper:
            return f"contiene '{word}'"

    if _PERCENTAGE.search(text):
        return "contiene un porcentaje"

    for match in _PAGE_REFERENCE.finditer(text):
        page = int(match.group(1))
        if page not in finding.pages:
            return f"cita la pagina {page}, que no consta como evidencia de este hallazgo"

    return None


def draft_prose(
    findings: List[Finding],
    case: Dict[str, Any],
    municipality: str,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Ask for prose, then reconcile it against the findings we already decided.

    Returns (sections, model_used). Every finding comes back with text whether
    or not the model produced usable output for it.
    """
    codes = [f.rule_code for f in findings]
    written: Dict[str, Dict[str, str]] = {}
    introduccion = ""
    cierre = ""
    model_used = None

    client = _client()
    if client is not None:
        model = get_settings().reviewer_model
        try:
            response = client.messages.create(
                model=model,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                output_config={
                    "format": {"type": "json_schema", "schema": _schema(codes)},
                    "effort": "high",
                },
                messages=[{"role": "user", "content": _prompt(findings, case, municipality)}],
            )

            if getattr(response, "stop_reason", None) != "refusal":
                text = next(b.text for b in response.content if b.type == "text")
                parsed = json.loads(text)
                introduccion = (parsed.get("introduccion") or "").strip()
                cierre = (parsed.get("cierre") or "").strip()
                model_used = model

                for entry in parsed.get("hallazgos") or []:
                    code = entry.get("rule_code")
                    # A code we did not send is discarded outright: the model
                    # cannot introduce a finding.
                    if code in codes:
                        written[code] = {
                            "parrafo": (entry.get("parrafo") or "").strip(),
                            "subsanacion": (entry.get("subsanacion") or "").strip(),
                            "generado": "modelo",
                        }
        except Exception as exc:
            logger.warning("Requerimiento drafting failed: %s", exc)

    hallazgos = []
    for index, finding in enumerate(findings, start=1):
        text = written.get(finding.rule_code)

        if text and text["parrafo"]:
            combined = f"{text['parrafo']} {text['subsanacion']}"
            problem = _validate(combined, finding)
            if problem:
                logger.warning(
                    "Discarding drafted text for %s: %s", finding.rule_code, problem
                )
                text = {**_fallback(finding), "descartado_por": problem}
        else:
            text = _fallback(finding)

        hallazgos.append(
            {
                "numero": index,
                "rule_code": finding.rule_code,
                "titulo": finding.title,
                "severidad": finding.severity,
                "parrafo": text["parrafo"],
                "subsanacion": text["subsanacion"],
                "fundamento": finding.citation,
                "generado": text.get("generado", "sistema"),
                "descartado_por": text.get("descartado_por"),
                # Citations are appended by the system, never written by the model.
                "evidencia": [
                    {
                        "documento": e["documento"],
                        "pagina": e["pagina"],
                        "valor": e.get("valor"),
                    }
                    for e in finding.evidence
                    if e.get("pagina")
                ],
            }
        )

    if not introduccion or _validate(introduccion, findings[0]):
        introduccion = (
            "Tras examinar los documentos radicados con la solicitud de referencia, "
            "esta oficina identifico los senalamientos que se detallan a continuacion. "
            "Se le requiere subsanarlos para continuar con el tramite."
        )

    if not cierre or _validate(cierre, findings[0]):
        cierre = (
            "Debera presentar la documentacion requerida ante esta oficina dentro del "
            "termino que dispone la reglamentacion aplicable. De no atenderse este "
            "requerimiento, la solicitud podra ser archivada."
        )

    return {"introduccion": introduccion, "hallazgos": hallazgos, "cierre": cierre}, model_used


# =============================================================================
# Building and persisting
# =============================================================================

def build(ctx: ReviewerContext, case_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new draft notice. Returns the stored row, or an error dict."""
    findings, pending = collect(ctx, case_id, case.get("ruleset_version_id"))

    if not findings:
        return {
            "error": (
                "No hay hallazgos identificados en este expediente, por lo que no "
                "procede un requerimiento de subsanacion."
                + (
                    f" Quedan {len(pending)} verificaciones que requieren criterio "
                    "del revisor; resuelvalas antes de generar el documento."
                    if pending
                    else ""
                )
            ),
            "pendientes": pending,
        }

    sections, model_used = draft_prose(findings, case, ctx.municipality)

    existing = ctx.db.select(
        "requerimientos",
        columns="version",
        filters={"case_id": f"eq.{case_id}"},
        order="version.desc",
        limit=1,
    )
    version = (existing[0]["version"] + 1) if existing else 1

    body = {
        "encabezado": {
            "municipio": ctx.municipality,
            "oficina": ctx.org_name,
            "case_number": case.get("case_number"),
            "solicitante": case.get("applicant_name"),
            "direccion": case.get("property_address"),
            "catastro": case.get("catastro"),
            "fecha": date.today().isoformat(),
            "ruleset_version_id": case.get("ruleset_version_id"),
        },
        **sections,
        # Carried so the notice can say what it does NOT cover.
        "pendientes_de_criterio": pending,
    }

    rows = ctx.db.insert(
        "requerimientos",
        {
            "case_id": case_id,
            "org_id": ctx.org_id,
            "ruleset_version_id": case.get("ruleset_version_id"),
            "version": version,
            "status": "borrador",
            "finding_ids": [f.check_id for f in findings],
            "body": body,
            "model_used": model_used,
            "generated_by": str(ctx.user_id),
        },
    )

    audit.record(
        ctx,
        REQUERIMIENTO_DRAFTED,
        case_id=case_id,
        object_ref=rows[0]["id"] if rows else None,
        payload={
            "version": version,
            "hallazgos": len(findings),
            "pendientes": len(pending),
            "model_used": model_used,
        },
    )

    return rows[0] if rows else {"error": "No se pudo guardar el requerimiento."}


def approve(ctx: ReviewerContext, requerimiento_id: str) -> Dict[str, Any]:
    """
    Record a reviewer's approval.

    This marks the document as approved. It does not send it anywhere, and there
    is no code path in this system that does.
    """
    from datetime import datetime, timezone

    current = ctx.db.select_one(
        "requerimientos",
        columns="id,case_id,status,version",
        filters={"id": f"eq.{requerimiento_id}"},
    )
    if not current:
        return {"error": "Requerimiento no encontrado."}
    if current["status"] == "aprobado":
        return {"error": "Este requerimiento ya fue aprobado."}
    if current["status"] == "descartado":
        return {"error": "Este requerimiento fue descartado."}

    rows = ctx.db.update(
        "requerimientos",
        filters={"id": f"eq.{requerimiento_id}"},
        values={
            "status": "aprobado",
            "approved_by": str(ctx.user_id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    audit.record(
        ctx,
        REQUERIMIENTO_APPROVED,
        case_id=current["case_id"],
        object_ref=requerimiento_id,
        payload={"version": current["version"]},
    )

    return rows[0] if rows else {"error": "No se pudo aprobar el requerimiento."}


def latest(ctx: ReviewerContext, case_id: str) -> Optional[Dict[str, Any]]:
    rows = ctx.db.select(
        "requerimientos",
        columns=(
            "id,case_id,version,status,finding_ids,body,model_used,"
            "generated_at,approved_at,generated_by,approved_by"
        ),
        filters={"case_id": f"eq.{case_id}"},
        order="version.desc",
        limit=1,
    )
    return rows[0] if rows else None
