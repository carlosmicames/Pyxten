"""
The deterministic rule engine.

These tests are the specification: three-valued logic, evaluation order, and the
four safety nets that can only soften an outcome, never harden one.
"""
from datetime import date

import pytest

from app.reviewer.rules import (
    HALLAZGO_IDENTIFICADO,
    REQUIERE_CRITERIO,
    SIN_HALLAZGOS,
    Context,
    ExternalResult,
    Fact,
    Tri,
    evaluate_case,
    evaluate_rule,
    summarize,
    validate_condition,
)
from app.reviewer.rules.grammar import evaluate
from app.reviewer.rules.tri import tri_all, tri_any, tri_not


# =============================================================================
# Three-valued logic
# =============================================================================

def test_conjunction_false_beats_unknown():
    """One definitely-unmet requirement settles it, whatever else is unclear."""
    assert tri_all([Tri.TRUE, Tri.UNKNOWN, Tri.FALSE]) is Tri.FALSE
    assert tri_all([Tri.TRUE, Tri.UNKNOWN]) is Tri.UNKNOWN
    assert tri_all([Tri.TRUE, Tri.TRUE]) is Tri.TRUE


def test_disjunction_true_beats_unknown():
    assert tri_any([Tri.FALSE, Tri.UNKNOWN, Tri.TRUE]) is Tri.TRUE
    assert tri_any([Tri.FALSE, Tri.UNKNOWN]) is Tri.UNKNOWN
    assert tri_any([Tri.FALSE, Tri.FALSE]) is Tri.FALSE


def test_negation_of_unknown_is_still_unknown():
    assert tri_not(Tri.UNKNOWN) is Tri.UNKNOWN
    assert tri_not(Tri.TRUE) is Tri.FALSE


# =============================================================================
# Predicates
# =============================================================================

def make_ctx(**overrides) -> Context:
    ctx = Context(
        facts={
            "patente.nombre_solicitante": Fact(
                "patente.nombre_solicitante", value_text="Panaderia Lopez Inc.",
                document_id="doc-patente", source_page=1, band="alta",
            ),
            "registro.nombre_solicitante": Fact(
                "registro.nombre_solicitante", value_text="Panadería López Corp.",
                document_id="doc-registro", source_page=2, band="alta",
            ),
            "bomberos.fecha_vencimiento": Fact(
                "bomberos.fecha_vencimiento", value_date=date(2027, 1, 15),
                document_id="doc-bomberos", source_page=1, band="alta",
            ),
            "bomberos.entidad_emisora": Fact(
                "bomberos.entidad_emisora",
                value_text="Negociado del Cuerpo de Bomberos de Puerto Rico",
                document_id="doc-bomberos", source_page=1, band="alta",
            ),
        },
        document_types=["patente_municipal", "registro_comerciante", "certificado_bomberos"],
        document_ids_by_type={
            "patente_municipal": "doc-patente",
            "registro_comerciante": "doc-registro",
            "certificado_bomberos": "doc-bomberos",
        },
        profile={"tenencia": "arrendatario", "acceso_publico": True},
        case={"filing_date": "2026-03-01", "catastro": "123-456-789-01"},
        externals={"crim_parcelas": ExternalResult("crim_parcelas", value="12345678901", matched=True)},
    )
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


def test_doc_present_and_absent():
    ctx = make_ctx()
    assert evaluate({"doc_present": {"type": "patente_municipal"}}, ctx) is Tri.TRUE
    assert evaluate({"doc_present": {"type": "certificado_salud"}}, ctx) is Tri.FALSE


def test_missing_fact_is_unknown_not_false():
    """The whole point of three-valued logic."""
    ctx = make_ctx()
    assert evaluate(
        {"field_equals": {"left": "salud.nombre", "right": "case.applicant_name"}}, ctx
    ) is Tri.UNKNOWN


def test_unanswered_profile_question_is_unknown():
    ctx = make_ctx(profile={})
    assert evaluate({"profile_is": {"key": "tenencia", "value": "dueno"}}, ctx) is Tri.UNKNOWN


def test_entity_names_agree_across_documents():
    ctx = make_ctx()
    outcome = evaluate(
        {"field_equals": {
            "left": "patente.nombre_solicitante",
            "right": "registro.nombre_solicitante",
            "normalize": "entity_name",
        }},
        ctx,
    )
    assert outcome is Tri.TRUE
    # Both sides were cited, which is what makes a finding defensible.
    assert set(ctx.evidence) == {"doc-patente", "doc-registro"}


def test_low_band_reading_never_concludes_a_comparison():
    ctx = make_ctx()
    ctx.facts["registro.nombre_solicitante"].band = "baja"
    outcome = evaluate(
        {"field_equals": {
            "left": "patente.nombre_solicitante",
            "right": "registro.nombre_solicitante",
            "normalize": "entity_name",
        }},
        ctx,
    )
    assert outcome is Tri.UNKNOWN
    assert "banda_baja_en_comparacion" in ctx.notes


def test_date_validity_and_illegible_date():
    ctx = make_ctx()
    assert evaluate(
        {"date_on_or_after": {"field": "bomberos.fecha_vencimiento", "reference": "case.filing_date"}},
        ctx,
    ) is Tri.TRUE

    ctx.facts["bomberos.fecha_vencimiento"] = Fact(
        "bomberos.fecha_vencimiento", value_text="ilegible",
        document_id="doc-bomberos", source_page=1,
    )
    assert evaluate(
        {"date_on_or_after": {"field": "bomberos.fecha_vencimiento", "reference": "case.filing_date"}},
        ctx,
    ) is Tri.UNKNOWN


def test_issuing_entity_matched_by_keyword():
    ctx = make_ctx()
    assert evaluate(
        {"issued_by": {"field": "bomberos.entidad_emisora", "keywords": ["bomberos"]}}, ctx
    ) is Tri.TRUE
    assert evaluate(
        {"issued_by": {"field": "bomberos.entidad_emisora", "keywords": ["asume"]}}, ctx
    ) is Tri.FALSE


def test_external_disagreement_escalates_and_never_accuses():
    """
    GIS is evidence, not truth. A mismatch is UNKNOWN with both values recorded -
    this predicate has no path to producing a finding against the applicant.
    """
    ctx = make_ctx()
    ctx.facts["solicitud.catastro"] = Fact(
        "solicitud.catastro", value_text="999-888-777-66",
        document_id="doc-solicitud", source_page=1, band="alta",
    )
    outcome = evaluate(
        {"external_agrees": {
            "source": "crim_parcelas", "field": "solicitud.catastro", "normalize": "catastro",
        }},
        ctx,
    )
    assert outcome is Tri.UNKNOWN
    assert any(n.startswith("discrepancia_externa:") for n in ctx.notes)


@pytest.mark.parametrize("flag", ["ambiguo", "fuera_de_servicio", "esquema_inesperado"])
def test_unusable_external_lookup_escalates(flag):
    ctx = make_ctx()
    ctx.externals["crim_parcelas"] = ExternalResult("crim_parcelas", value="x", quality_flag=flag)
    ctx.facts["solicitud.catastro"] = Fact(
        "solicitud.catastro", value_text="123-456-789-01", document_id="d", source_page=1,
    )
    assert evaluate(
        {"external_agrees": {"source": "crim_parcelas", "field": "solicitud.catastro"}}, ctx
    ) is Tri.UNKNOWN


def test_unknown_predicate_escalates_rather_than_passing():
    ctx = make_ctx()
    assert evaluate({"inventado": {"x": 1}}, ctx) is Tri.UNKNOWN
    assert "predicado_desconocido:inventado" in ctx.notes


def test_empty_condition_is_unknown_not_vacuously_true():
    assert evaluate({}, make_ctx()) is Tri.UNKNOWN
    assert evaluate(None, make_ctx()) is Tri.UNKNOWN


# =============================================================================
# Rule evaluation and the safety nets
# =============================================================================

PRESENCE_RULE = {
    "id": "r1", "code": "P-05", "family": "presencia",
    "title": "Certificado de bomberos presente",
    "citation": "Reglamento Conjunto 2023",
    "pass_condition": {"doc_present": {"type": "certificado_bomberos"}},
    "fail_condition": {"not": {"doc_present": {"type": "certificado_bomberos"}}},
}


def test_rule_passes_when_document_present():
    result = evaluate_rule(PRESENCE_RULE, make_ctx())
    assert result.status == SIN_HALLAZGOS


def test_rule_finds_when_document_absent():
    ctx = make_ctx(document_types=["patente_municipal"], document_ids_by_type={"patente_municipal": "doc-p"})
    rule = dict(PRESENCE_RULE)
    # Give the finding something to point at, or net 1 correctly suppresses it.
    rule["fail_condition"] = {"all": [
        {"not": {"doc_present": {"type": "certificado_bomberos"}}},
        {"doc_present": {"type": "patente_municipal"}},
    ]}
    result = evaluate_rule(rule, ctx)
    assert result.status == HALLAZGO_IDENTIFICADO
    assert result.evidence_ids


def test_inapplicable_rule_produces_no_row():
    rule = dict(PRESENCE_RULE, applies_when={"profile_is": {"key": "tenencia", "value": "dueno"}})
    assert evaluate_rule(rule, make_ctx()) is None


def test_indeterminate_applicability_escalates():
    rule = dict(PRESENCE_RULE, applies_when={"profile_is": {"key": "acceso_publico", "value": True}})
    ctx = make_ctx(profile={})
    result = evaluate_rule(rule, ctx)
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "aplicabilidad_indeterminada"


def test_review_condition_beats_both_pass_and_fail():
    rule = dict(
        PRESENCE_RULE,
        review_condition={"doc_present": {"type": "certificado_bomberos"}},
    )
    result = evaluate_rule(rule, make_ctx())
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "condicion_de_revision"


# --- net 1 -------------------------------------------------------------------

def test_finding_without_evidence_is_downgraded():
    """A finding that points at nothing is not a finding."""
    rule = {
        "id": "r2", "code": "X-01", "family": "presencia", "title": "Sin evidencia",
        "citation": "RC 2023",
        "fail_condition": {"not": {"doc_present": {"type": "certificado_salud"}}},
    }
    result = evaluate_rule(rule, make_ctx())
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "hallazgo_sin_evidencia"


# --- net 2 -------------------------------------------------------------------

def test_consistency_finding_must_cite_both_documents():
    """
    A contradiction claim names both sides. One document cited is not enough to
    assert that two documents disagree.
    """
    ctx = make_ctx()
    rule = {
        "id": "r3", "code": "C-01", "family": "consistencia",
        "title": "Nombre concuerda", "citation": "RC 2023",
        # Deliberately reads only one document.
        "fail_condition": {"doc_present": {"type": "patente_municipal"}},
    }
    result = evaluate_rule(rule, ctx)
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "inconsistencia_sin_ambos_documentos"


def test_consistency_finding_with_both_sides_survives_and_quotes_them():
    ctx = make_ctx()
    ctx.facts["registro.nombre_solicitante"].value_text = "Ferreteria Marte LLC"
    rule = {
        "id": "r4", "code": "C-01", "family": "consistencia",
        "title": "Nombre del solicitante concuerda entre patente y registro",
        "citation": "Reglamento Conjunto 2023",
        "fail_condition": {"not": {"field_equals": {
            "left": "patente.nombre_solicitante",
            "right": "registro.nombre_solicitante",
            "normalize": "entity_name",
        }}},
    }
    result = evaluate_rule(rule, ctx)

    assert result.status == HALLAZGO_IDENTIFICADO
    assert len(set(result.evidence_ids)) >= 2
    # The explanation names both values, both documents and both pages.
    assert "Panaderia Lopez Inc." in result.explanation
    assert "Ferreteria Marte LLC" in result.explanation
    assert "doc-patente" in result.explanation
    assert "doc-registro" in result.explanation
    assert "Reglamento Conjunto 2023" in result.explanation


# --- net 3 -------------------------------------------------------------------

def test_uncited_rule_may_escalate_but_never_accuse():
    ctx = make_ctx(document_types=["patente_municipal"],
                   document_ids_by_type={"patente_municipal": "doc-p"})
    rule = {
        "id": "r5", "code": "X-02", "family": "presencia",
        "title": "Sin fundamento legal", "citation": None,
        "fail_condition": {"doc_present": {"type": "patente_municipal"}},
    }
    result = evaluate_rule(rule, ctx)
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "regla_sin_fundamento_legal"


# --- net 4 -------------------------------------------------------------------

def test_low_band_forces_escalation_whatever_the_logic_concluded():
    ctx = make_ctx()
    for fact in ctx.facts.values():
        fact.band = "baja"

    rule = {
        "id": "r6", "code": "V-03", "family": "vigencia",
        "title": "Bomberos vigente", "citation": "RC 2023",
        "pass_condition": {"field_present": {"field": "bomberos.fecha_vencimiento"}},
    }
    result = evaluate_rule(rule, ctx)
    assert result.band == "baja"
    assert result.status == REQUIERE_CRITERIO
    assert result.reason_code == "banda_baja"


def test_band_is_the_weakest_reading_used():
    ctx = make_ctx()
    ctx.facts["registro.nombre_solicitante"].band = "media"
    rule = {
        "id": "r7", "code": "C-06", "family": "consistencia",
        "title": "Nombre comercial", "citation": "RC 2023",
        "pass_condition": {"field_equals": {
            "left": "patente.nombre_solicitante",
            "right": "registro.nombre_solicitante",
            "normalize": "entity_name",
        }},
    }
    assert evaluate_rule(rule, ctx).band == "media"


# =============================================================================
# Whole-case behaviour
# =============================================================================

def test_a_rule_that_raises_becomes_an_escalation_not_a_gap():
    class Exploding(dict):
        def get(self, key, default=None):
            if key == "applies_when":
                raise RuntimeError("boom")
            return super().get(key, default)

    rule = Exploding({"id": "r8", "code": "BAD", "family": "presencia", "title": "Rota"})
    results = evaluate_case([rule], make_ctx())

    assert len(results) == 1
    assert results[0].status == REQUIERE_CRITERIO
    assert results[0].reason_code == "error_de_evaluacion"


def test_disabled_rules_are_skipped():
    assert evaluate_case([dict(PRESENCE_RULE, enabled=False)], make_ctx()) == []


def test_summary_counts_states_and_asserts_no_overall_verdict():
    results = evaluate_case([PRESENCE_RULE], make_ctx())
    summary = summarize(results)

    assert summary[SIN_HALLAZGOS] == 1
    assert summary["total_evaluadas"] == 1
    # No case-level determination is produced. The three states describe checks,
    # not the application as a whole.
    assert "viable" not in summary
    assert "overall" not in summary


# =============================================================================
# Authoring-time validation
# =============================================================================

def test_validator_catches_typos_before_a_ruleset_is_published():
    problems = validate_condition({"all": [
        {"doc_present": {"type": "x"}},
        {"predicado_inventado": {}},
        {"field_equals": {"left": "a", "right": "b", "normalize": "no_existe"}},
    ]})
    assert any("predicado desconocido" in p for p in problems)
    assert any("normalizador desconocido" in p for p in problems)


def test_validator_accepts_a_well_formed_rule():
    assert validate_condition({"all": [
        {"doc_present": {"type": "certificado_bomberos"}},
        {"date_on_or_after": {"field": "bomberos.fecha_vencimiento", "reference": "case.filing_date"}},
    ]}) == []
