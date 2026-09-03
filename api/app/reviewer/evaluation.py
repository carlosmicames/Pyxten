"""
Running a case: extract the facts, then evaluate the rules against them.

Both passes are append-only. Re-extracting a case after a document is replaced
adds new fact rows rather than overwriting old ones, and the context builder
takes the most recent reading of each field. That keeps "what did the system
conclude, and from what, on the day the notice went out" answerable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.reviewer import audit, intake
from app.reviewer.context import ReviewerContext
from app.reviewer.extraction import extract_document
from app.reviewer.pdf_text import analyze_pdf
from app.reviewer.rules import Context, Fact, evaluate_case, summarize

logger = logging.getLogger(__name__)

EXTRACTION_RUN = "extraction_run"
EVALUATION_RUN = "evaluation_run"

_DOCUMENT_FIELDS = "id,doc_type,classification_band,storage_uri,filename,processing_status"


# =============================================================================
# Extraction
# =============================================================================

def run_extraction(ctx: ReviewerContext, case_id: str) -> Dict[str, Any]:
    """
    Extract facts from every classified document on the case.

    A document typed `desconocido`, or one whose type no rule reads, is skipped -
    there is nothing defined to look for. That is reported rather than hidden,
    because unextracted documents are why a case may have thin evidence.
    """
    documents = ctx.db.select(
        "case_documents",
        columns=_DOCUMENT_FIELDS,
        filters={"case_id": f"eq.{case_id}"},
        order="uploaded_at.asc",
    )

    processed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    total_facts = 0

    for document in documents:
        doc_type = document.get("doc_type")

        if doc_type == "desconocido" or not doc_type:
            skipped.append({"document_id": document["id"], "reason": "sin_clasificar"})
            continue

        try:
            content = ctx.db.storage_download(intake.BUCKET, document["storage_uri"])
        except Exception as exc:
            logger.error("Could not download %s: %s", document["id"], exc)
            skipped.append({"document_id": document["id"], "reason": f"descarga_fallida: {exc}"})
            continue

        analysis = analyze_pdf(content)
        facts, error = extract_document(analysis, content, doc_type)

        if not facts:
            skipped.append({"document_id": document["id"], "reason": "sin_campos_definidos"})
            continue

        rows = [f.as_row(case_id, ctx.org_id, document["id"]) for f in facts]
        try:
            ctx.db.insert("extracted_facts", rows, returning=False)
        except Exception as exc:
            logger.error("Could not store facts for %s: %s", document["id"], exc)
            skipped.append({"document_id": document["id"], "reason": f"guardado_fallido: {exc}"})
            continue

        located = sum(1 for f in facts if f.status == "extraido")
        total_facts += len(facts)
        processed.append(
            {
                "document_id": document["id"],
                "doc_type": doc_type,
                "campos": len(facts),
                "localizados": located,
                "error": error,
            }
        )

    audit.record(
        ctx,
        EXTRACTION_RUN,
        case_id=case_id,
        object_ref=case_id,
        payload={"documentos": len(processed), "omitidos": len(skipped), "campos": total_facts},
    )

    return {"procesados": processed, "omitidos": skipped, "campos_totales": total_facts}


# =============================================================================
# Context assembly
# =============================================================================

def build_context(ctx: ReviewerContext, case_id: str, case: Dict[str, Any]) -> Context:
    """
    Assemble everything the rules may look at.

    Facts are read newest-first and the first reading of each field wins, so a
    re-extraction supersedes an older one without deleting it.
    """
    documents = ctx.db.select(
        "case_documents",
        columns=_DOCUMENT_FIELDS,
        filters={"case_id": f"eq.{case_id}"},
        order="uploaded_at.asc",
    )

    document_ids_by_type: Dict[str, str] = {}
    document_bands: Dict[str, str] = {}
    for document in documents:
        doc_type = document.get("doc_type")
        if not doc_type:
            continue
        # First upload of a type wins as the citable one; a second copy does not
        # change what the rules can point at.
        document_ids_by_type.setdefault(doc_type, document["id"])
        document_bands.setdefault(doc_type, document.get("classification_band") or "media")

    rows = ctx.db.select(
        "extracted_facts",
        columns="field_key,value_text,value_date,value_num,document_id,source_page,band,status,extracted_at",
        filters={"case_id": f"eq.{case_id}"},
        order="extracted_at.desc",
    )

    facts: Dict[str, Fact] = {}
    for row in rows:
        key = row["field_key"]
        if key in facts:
            continue  # newest wins
        facts[key] = Fact(
            field_key=key,
            value_text=row.get("value_text"),
            value_date=row.get("value_date"),
            value_num=row.get("value_num"),
            document_id=row.get("document_id"),
            source_page=row.get("source_page"),
            band=row.get("band") or "media",
            status=row.get("status") or "extraido",
        )

    externals = _load_externals(ctx, case_id)

    return Context(
        facts=facts,
        document_types=list(document_ids_by_type.keys()),
        document_ids_by_type=document_ids_by_type,
        document_bands=document_bands,
        profile=case.get("profile") or {},
        case={
            "filing_date": case.get("filing_date"),
            "catastro": case.get("catastro"),
            "applicant_name": case.get("applicant_name"),
            "property_address": case.get("property_address"),
        },
        externals=externals,
    )


def _load_externals(ctx: ReviewerContext, case_id: str) -> Dict[str, Any]:
    """
    Most recent external lookup per source.

    Nothing writes these yet - the GIS wrapper lands with the zoning rule - so
    this is normally empty, and the rules that need a lookup escalate with
    `consulta_externa_ausente`. That is the correct behaviour, not a gap.
    """
    from app.reviewer.rules import ExternalResult

    try:
        rows = ctx.db.select(
            "external_verifications",
            columns="source,response,matched,quality_flag,retrieved_at",
            filters={"case_id": f"eq.{case_id}"},
            order="retrieved_at.desc",
        )
    except Exception as exc:
        logger.warning("Could not load external verifications: %s", exc)
        return {}

    externals: Dict[str, Any] = {}
    for row in rows:
        source = row.get("source")
        if not source or source in externals:
            continue
        response = row.get("response") or {}
        externals[source] = ExternalResult(
            source=source,
            value=response.get("value"),
            matched=bool(row.get("matched")),
            quality_flag=row.get("quality_flag") or "ok",
        )
    return externals


# =============================================================================
# Evaluation
# =============================================================================

def load_rules(ctx: ReviewerContext, ruleset_id: str) -> List[Dict[str, Any]]:
    return ctx.db.select(
        "rules",
        columns=(
            "id,code,title,family,authority,citation,applies_when,required_evidence,"
            "pass_condition,fail_condition,review_condition,severity,enabled"
        ),
        filters={"ruleset_id": f"eq.{ruleset_id}", "enabled": "eq.true"},
        order="code.asc",
    )


def run_evaluation(ctx: ReviewerContext, case_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate the case against the ruleset it was stamped with at intake.

    Note which ruleset: the case's own `ruleset_version_id`, not the office's
    current one. That is the whole point of the stamp.
    """
    ruleset_id = case.get("ruleset_version_id")
    if not ruleset_id:
        return {"error": "El expediente no tiene una version de reglamento asociada."}

    rules = load_rules(ctx, ruleset_id)
    if not rules:
        return {
            "error": (
                "El reglamento asociado a este expediente no tiene reglas activas. "
                "Ejecute la migracion 007 para sembrarlas."
            )
        }

    context = build_context(ctx, case_id, case)
    results = evaluate_case(rules, context)

    rows = [r.as_row(case_id, ctx.org_id) for r in results]
    if rows:
        try:
            ctx.db.insert("compliance_checks", rows, returning=False)
        except Exception as exc:
            logger.error("Could not store checks for case %s: %s", case_id, exc)
            return {"error": f"No se pudieron guardar los resultados: {exc}"}

    summary = summarize(results)

    audit.record(
        ctx,
        EVALUATION_RUN,
        case_id=case_id,
        object_ref=ruleset_id,
        payload={"ruleset_id": ruleset_id, "resumen": summary},
    )

    return {
        "resumen": summary,
        "ruleset_id": ruleset_id,
        "verificaciones": [
            {
                "rule_code": r.rule_code,
                "family": r.family,
                "status": r.status,
                "band": r.band,
                "reason_code": r.reason_code,
                "explanation": r.explanation,
                "evidence_ids": r.evidence_ids,
                "citations": r.citations,
            }
            for r in results
        ],
    }
