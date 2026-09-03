"""
The deterministic evaluator.

No model is imported here and none ever should be. Rules are data; this file is
the interpreter that turns a rule plus a set of extracted facts into one
compliance_checks row. Every outcome is reproducible from the same inputs.

Evaluation order per rule is deliberately boring:

  1. applies_when false  -> no row at all, the rule is not relevant to this case
  2. review_condition    -> requiere_criterio   (tested FIRST, so an ambiguity or
                            a missing document wins over both a pass and a fail)
  3. fail_condition      -> hallazgo_identificado
  4. pass_condition      -> sin_hallazgos
  5. none of the above   -> requiere_criterio, reason `condiciones_no_concluyentes`

Then four safety nets, applied after the logic and able only to soften an
outcome, never to harden one:

  * a finding with no evidence becomes requiere_criterio
  * a consistency finding citing fewer than two documents becomes
    requiere_criterio - a contradiction claim has to name both sides
  * a rule with no legal citation cannot produce a finding
  * a low band forces requiere_criterio
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.reviewer.rules.grammar import Context, evaluate
from app.reviewer.rules.tri import Tri

logger = logging.getLogger(__name__)

# The three decision states. Exact identifiers - never paraphrased, and the
# Spanish display strings live in one place on the frontend.
SIN_HALLAZGOS = "sin_hallazgos"
HALLAZGO_IDENTIFICADO = "hallazgo_identificado"
REQUIERE_CRITERIO = "requiere_criterio"

FAMILY_CONSISTENCY = "consistencia"
FAMILY_PRESENCE = "presencia"

# Worst band wins: a conclusion is only as good as its weakest reading.
_BAND_ORDER = {"alta": 3, "media": 2, "baja": 1}


@dataclass
class CheckResult:
    rule_id: str
    rule_code: str
    family: str
    status: str
    band: str
    reason_code: Optional[str]
    explanation: str
    evidence_ids: List[str] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)

    def as_row(self, case_id: str, org_id: str) -> Dict[str, Any]:
        """Shape for insertion into compliance_checks."""
        return {
            "case_id": case_id,
            "org_id": org_id,
            "rule_id": self.rule_id,
            "family": self.family,
            "status": self.status,
            "band": self.band,
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "evidence_ids": self.evidence_ids,
            "citations": self.citations,
        }


def _band_from_citations(citations: List[Dict[str, Any]]) -> str:
    """
    The check's band is the weakest band among the facts it actually read.
    Derived, never asked of a model, and never a number.
    """
    bands = [c.get("band") for c in citations if c.get("band") in _BAND_ORDER]
    if not bands:
        # Nothing was read. That is not high confidence.
        return "baja"
    return min(bands, key=lambda b: _BAND_ORDER[b])


def _describe(rule: Dict[str, Any], ctx: Context, status: str) -> str:
    """
    Machine-generated explanation.

    Deliberately mechanical: it states what was compared and what was seen, with
    document and page. No prose is drafted here - that happens later, from these
    findings, and only for a reviewer to approve.
    """
    title = rule.get("title") or rule.get("code", "")
    parts = [title]

    if status == HALLAZGO_IDENTIFICADO and rule.get("family") == FAMILY_CONSISTENCY:
        # A contradiction claim must name both sides and the difference.
        #
        # Only field readings qualify. `applies_when` runs first and cites the
        # documents it checked for presence, so without this filter the notice
        # would quote document type names instead of the values that disagree.
        seen = [
            c for c in ctx.citations
            if c.get("value")
            and not c["field_key"].startswith(("documento.", "expediente."))
        ]
        if len(seen) >= 2:
            left, right = seen[0], seen[1]
            parts.append(
                f"Discrepancia: '{left['value']}' (documento {left['document_id']}, "
                f"p. {left['page']}) frente a '{right['value']}' "
                f"(documento {right['document_id']}, p. {right['page']})."
            )
    elif status == HALLAZGO_IDENTIFICADO and rule.get("family") == FAMILY_PRESENCE:
        # A presence finding is about an absence, and the rule title is phrased
        # as the satisfied state ("Certificado de bomberos presente"). Saying
        # what is missing, against what was reviewed, is what belongs in a notice.
        inventory = next(
            (c for c in ctx.citations if c["field_key"] == "expediente.inventario"), None
        )
        required = rule.get("required_evidence") or []
        missing = ", ".join(required) if required else "el documento requerido"
        if inventory and inventory.get("value"):
            parts.append(
                f"No se localizo {missing} entre los documentos radicados "
                f"({inventory['value']})."
            )
        else:
            parts.append(f"No se localizo {missing} en el expediente.")

    elif ctx.citations:
        located = [c for c in ctx.citations if c.get("document_id")]
        if located:
            refs = "; ".join(
                f"{c['field_key']} = '{c.get('value')}' (doc {c['document_id']}, p. {c.get('page')})"
                for c in located[:4]
            )
            parts.append(f"Evidencia: {refs}.")

    if ctx.notes:
        parts.append(f"Notas: {', '.join(dict.fromkeys(ctx.notes))}.")

    citation = rule.get("citation")
    if citation:
        parts.append(f"Fundamento: {citation}.")

    return " ".join(p for p in parts if p)


def evaluate_rule(rule: Dict[str, Any], ctx: Context) -> Optional[CheckResult]:
    """
    Evaluate one rule. Returns None when the rule does not apply to this case.
    """
    ctx.reset_evidence()

    # --- 1. Applicability -----------------------------------------------------
    applies_when = rule.get("applies_when")
    if applies_when:
        applicable = evaluate(applies_when, ctx)
        if applicable is Tri.FALSE:
            return None
        if applicable is Tri.UNKNOWN:
            # We cannot tell whether this rule is even relevant. That is a
            # reviewer's call, not a pass.
            return _result(
                rule, ctx, REQUIERE_CRITERIO, "aplicabilidad_indeterminada"
            )

    # --- 2-4. The three conditions, review first ------------------------------
    if evaluate(rule.get("review_condition"), ctx) is Tri.TRUE:
        return _result(rule, ctx, REQUIERE_CRITERIO, "condicion_de_revision")

    if evaluate(rule.get("fail_condition"), ctx) is Tri.TRUE:
        return _result(rule, ctx, HALLAZGO_IDENTIFICADO, None)

    if evaluate(rule.get("pass_condition"), ctx) is Tri.TRUE:
        return _result(rule, ctx, SIN_HALLAZGOS, None)

    # --- 5. Nothing concluded -------------------------------------------------
    return _result(rule, ctx, REQUIERE_CRITERIO, "condiciones_no_concluyentes")


def _result(
    rule: Dict[str, Any],
    ctx: Context,
    status: str,
    reason_code: Optional[str],
) -> CheckResult:
    """Apply the safety nets and assemble the row."""
    band = _band_from_citations(ctx.citations)
    evidence = list(ctx.evidence)
    family = rule.get("family", "")

    # Net 1: a finding with no evidence is not a finding.
    if status == HALLAZGO_IDENTIFICADO and not evidence:
        status, reason_code = REQUIERE_CRITERIO, "hallazgo_sin_evidencia"

    # Net 2: a contradiction has two sides, and the notice has to cite both.
    if (
        status == HALLAZGO_IDENTIFICADO
        and family == FAMILY_CONSISTENCY
        and len({c.get("document_id") for c in ctx.citations if c.get("document_id")}) < 2
    ):
        status, reason_code = REQUIERE_CRITERIO, "inconsistencia_sin_ambos_documentos"

    # Net 3: an uncited rule may escalate, but may not accuse.
    if status == HALLAZGO_IDENTIFICADO and not rule.get("citation"):
        status, reason_code = REQUIERE_CRITERIO, "regla_sin_fundamento_legal"

    # Net 4: a low band always escalates, whatever the logic concluded.
    if band == "baja" and status != REQUIERE_CRITERIO:
        status, reason_code = REQUIERE_CRITERIO, "banda_baja"

    if status == REQUIERE_CRITERIO and not reason_code:
        reason_code = "condiciones_no_concluyentes"

    return CheckResult(
        rule_id=rule.get("id", ""),
        rule_code=rule.get("code", ""),
        family=family,
        status=status,
        band=band,
        reason_code=reason_code,
        explanation=_describe(rule, ctx, status),
        evidence_ids=evidence,
        citations=list(ctx.citations),
    )


def evaluate_case(rules: List[Dict[str, Any]], ctx: Context) -> List[CheckResult]:
    """
    Run every enabled rule.

    A rule that raises is recorded as requiere_criterio rather than skipped: a
    crash in one rule must not quietly remove a check from the case.
    """
    results: List[CheckResult] = []

    for rule in rules:
        if rule.get("enabled") is False:
            continue
        try:
            outcome = evaluate_rule(rule, ctx)
        except Exception as exc:
            logger.exception("Rule %s failed to evaluate", rule.get("code"))
            outcome = CheckResult(
                rule_id=rule.get("id", ""),
                rule_code=rule.get("code", ""),
                family=rule.get("family", ""),
                status=REQUIERE_CRITERIO,
                band="baja",
                reason_code="error_de_evaluacion",
                explanation=(
                    f"{rule.get('title') or rule.get('code')}: la regla no se pudo "
                    f"evaluar ({exc.__class__.__name__}). Requiere revision manual."
                ),
            )

        if outcome is not None:
            results.append(outcome)

    return results


def summarize(results: List[CheckResult]) -> Dict[str, Any]:
    """
    Counts for the case screen.

    There is deliberately no overall case verdict here. The three states describe
    individual checks against the rules that were actually run; rolling them into
    a single case-level determination would assert something about the whole
    application that this system has not established.
    """
    return {
        SIN_HALLAZGOS: sum(1 for r in results if r.status == SIN_HALLAZGOS),
        HALLAZGO_IDENTIFICADO: sum(1 for r in results if r.status == HALLAZGO_IDENTIFICADO),
        REQUIERE_CRITERIO: sum(1 for r in results if r.status == REQUIERE_CRITERIO),
        "total_evaluadas": len(results),
    }
