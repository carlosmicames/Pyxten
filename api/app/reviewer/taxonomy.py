"""
The document taxonomy a case is classified into.

WHERE IT COMES FROM
The authority is `document_types`, keyed to a ruleset (migration 006). A
checklist change IS a rules change - a case decided under last year's checklist
has to keep resolving to last year's checklist - so the taxonomy is versioned
alongside the rules rather than living in code.

The Python list below is a fallback used only when the database has no types for
a ruleset, which happens before migration 006 has been applied. It is the
applicant product's list, and it describes a different permit; relying on it for
a Permiso Unico case would classify every business document as `desconocido`.
Callers that can reach the database should always pass a ruleset.

`desconocido` is a first-class outcome. A reviewer would rather see "I could not
tell" than a confident wrong label, so nothing here forces a guess.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

UNKNOWN = "desconocido"

_UNKNOWN_ENTRY = {
    "code": UNKNOWN,
    "name": "Desconocido",
    "description": (
        "El documento no corresponde claramente a ninguna categoria, "
        "o no hay evidencia suficiente para clasificarlo."
    ),
}


def _legacy_types() -> List[Dict[str, str]]:
    """The pre-migration list, kept only so nothing crashes before 006 is run."""
    types = [
        {"code": d["code"], "name": d["name"], "description": d["description"]}
        for d in DocumentService.get_permiso_unico_requirements()
    ]
    types.append(_UNKNOWN_ENTRY)
    return types


def types_for_ruleset(ctx, ruleset_id: Optional[str]) -> List[Dict[str, str]]:
    """
    The document types this ruleset classifies into, `desconocido` included.

    Falls back to the legacy list, loudly, when the database has none - a silent
    fallback here would mean classifying against the wrong permit's checklist.
    """
    if not ruleset_id:
        logger.warning("No ruleset given for taxonomy lookup; using the legacy list")
        return _legacy_types()

    try:
        rows = ctx.db.select(
            "document_types",
            columns="code,name,description,sort_order",
            filters={"ruleset_id": f"eq.{ruleset_id}"},
            order="sort_order.asc",
        )
    except Exception as exc:
        logger.error("Could not load document types for %s: %s", ruleset_id, exc)
        rows = []

    if not rows:
        logger.warning(
            "Ruleset %s has no document_types rows; using the legacy list. "
            "Run migration 006 if this is a Permiso Unico case.",
            ruleset_id,
        )
        return _legacy_types()

    types = [
        {"code": r["code"], "name": r["name"], "description": r.get("description") or ""}
        for r in rows
    ]
    if not any(t["code"] == UNKNOWN for t in types):
        types.append(_UNKNOWN_ENTRY)
    return types


def valid_codes(types: List[Dict[str, str]]) -> set:
    return {t["code"] for t in types}


def label_for(code: Optional[str], types: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Display name for a code. Falls back to the code itself rather than to a
    wrong label from another permit's checklist.
    """
    if not code:
        return "Desconocido"
    for entry in types or []:
        if entry["code"] == code:
            return entry["name"]
    return code


def catalog_for_prompt(types: List[Dict[str, str]]) -> str:
    """The taxonomy rendered for the classifier prompt, minus `desconocido`."""
    return "\n".join(
        f"- {t['code']}: {t['name']} - {t['description']}"
        for t in types
        if t["code"] != UNKNOWN
    )
