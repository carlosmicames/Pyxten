"""
The seeded ruleset, checked at build time.

Rules live in SQL, which means a typo in a predicate name would not surface
until a real case silently escalated. These tests parse migration 007, validate
every condition against the closed grammar, and run the whole ruleset against
synthetic cases.
"""
import json
import re
from pathlib import Path

import pytest

from app.reviewer.rules import (
    HALLAZGO_IDENTIFICADO,
    REQUIERE_CRITERIO,
    SIN_HALLAZGOS,
    Context,
    Fact,
    evaluate_case,
    summarize,
    validate_condition,
)

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "007_seed_rules.sql"

# Rows look like: ('CODE', 'Title', 'family', 'authority', citation, applies, req,
#                  pass, fail, review, 'severity', TRUE)
_ROW = re.compile(
    r"\(\s*'(?P<code>[A-Z]-\d{2})'\s*,\s*'(?P<title>[^']*)'\s*,\s*'(?P<family>\w+)'\s*,"
    r"\s*'(?P<authority>[^']*)'\s*,\s*(?P<citation>NULL|'[^']*')\s*,"
    r"\s*(?P<applies_when>NULL|'.*?')\s*,"
    r"\s*(?P<required_evidence>'.*?')\s*,"
    r"\s*(?P<pass_condition>NULL|'.*?')\s*,"
    r"\s*(?P<fail_condition>NULL|'.*?')\s*,"
    r"\s*(?P<review_condition>NULL|'.*?')\s*,"
    r"\s*'(?P<severity>\w+)'\s*,\s*(?P<enabled>TRUE|FALSE)\s*\)",
    re.DOTALL,
)

_JSON_FIELDS = (
    "applies_when",
    "required_evidence",
    "pass_condition",
    "fail_condition",
    "review_condition",
)


def _unquote(value):
    if value is None or value == "NULL":
        return None
    return value[1:-1] if value.startswith("'") else value


def load_seed_rules():
    text = MIGRATION.read_text(encoding="utf-8")
    rules = []

    for match in _ROW.finditer(text):
        rule = match.groupdict()
        rule["id"] = rule["code"]
        rule["enabled"] = rule["enabled"] == "TRUE"
        rule["citation"] = _unquote(rule["citation"])

        for key in _JSON_FIELDS:
            raw = _unquote(rule[key])
            rule[key] = json.loads(raw) if raw else None

        rules.append(rule)

    return rules


SEED_RULES = load_seed_rules()


# =============================================================================
# The ruleset parses and is what it claims to be
# =============================================================================

def test_all_rules_parsed():
    assert len(SEED_RULES) == 31, f"parsed {len(SEED_RULES)} rules, expected 31"


def test_family_counts_match_the_plan():
    counts = {}
    for rule in SEED_RULES:
        counts[rule["family"]] = counts.get(rule["family"], 0) + 1

    assert counts == {
        "presencia": 11,
        "vigencia": 11,
        "consistencia": 8,
        "aplicabilidad": 1,
    }


def test_rule_codes_are_unique():
    codes = [r["code"] for r in SEED_RULES]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("rule", SEED_RULES, ids=lambda r: r["code"])
def test_every_condition_is_valid_grammar(rule):
    """A predicate typo fails here rather than escalating a real case."""
    for key in ("applies_when", "pass_condition", "fail_condition", "review_condition"):
        condition = rule[key]
        if condition is None:
            continue
        problems = validate_condition(condition)
        assert not problems, f"{rule['code']}.{key}: {problems}"


@pytest.mark.parametrize("rule", SEED_RULES, ids=lambda r: r["code"])
def test_a_rule_that_can_accuse_must_carry_a_citation(rule):
    """
    Mirrors the rules_finding_requires_citation constraint in the database. An
    uncited rule may escalate to a reviewer; it may not produce a finding that
    ends up in a signed notice.
    """
    if rule["fail_condition"] is not None:
        assert rule["citation"], f"{rule['code']} can produce a finding with no citation"


@pytest.mark.parametrize("rule", SEED_RULES, ids=lambda r: r["code"])
def test_no_rule_invents_a_section_number(rule):
    """
    Citations name the instrument, not an article. A fabricated section
    reference in a requerimiento is worse than a general one, so until the RC
    text is on hand no rule may claim a specific article.
    """
    citation = rule["citation"] or ""
    assert not re.search(r"\b(sec|secci|art|articulo)\w*\.?\s*\d", citation, re.IGNORECASE), (
        f"{rule['code']} cites a specific article: {citation!r}. Verify it against the RC text first."
    )


def test_consistency_rules_read_two_documents():
    """
    Structural check on the family: a contradiction needs two sides, so every
    consistency rule's required_evidence names at least two document types.
    """
    for rule in SEED_RULES:
        if rule["family"] == "consistencia":
            assert len(rule["required_evidence"]) >= 2, rule["code"]


# =============================================================================
# The ruleset run against synthetic cases
# =============================================================================

def _fact(key, value, doc, page=1, band="alta"):
    return Fact(key, value_text=value, document_id=doc, source_page=page, band=band)


def complete_case_context() -> Context:
    """A well-formed application: everything present, current and consistent."""
    docs = {
        "registro_comerciante": "doc-reg",
        "patente_municipal": "doc-pat",
        "certificacion_crim": "doc-crim",
        "certificacion_asume": "doc-asume",
        "certificado_bomberos": "doc-bomb",
        "escritura_titularidad": "doc-esc",
        "plano_distribucion": "doc-plano",
    }
    return Context(
        facts={
            "registro_comerciante.nombre_solicitante": _fact("registro_comerciante.nombre_solicitante", "Panaderia Lopez Inc.", "doc-reg"),
            "patente_municipal.nombre_solicitante": _fact("patente_municipal.nombre_solicitante", "Panadería López Corp.", "doc-pat"),
            "registro_comerciante.nombre_comercial": _fact("registro_comerciante.nombre_comercial", "Panaderia Lopez", "doc-reg"),
            "patente_municipal.nombre_comercial": _fact("patente_municipal.nombre_comercial", "Panaderia Lopez", "doc-pat"),
            "registro_comerciante.actividad": _fact("registro_comerciante.actividad", "panaderia", "doc-reg"),
            "patente_municipal.actividad": _fact("patente_municipal.actividad", "panaderia", "doc-pat"),
            "registro_comerciante.estatus": _fact("registro_comerciante.estatus", "ACTIVO", "doc-reg"),
            "patente_municipal.periodo_hasta": _fact("patente_municipal.periodo_hasta", "2026-12-31", "doc-pat"),
            "patente_municipal.direccion_negocio": _fact("patente_municipal.direccion_negocio", "Calle Loiza 500, San Juan", "doc-pat"),
            "certificado_bomberos.direccion_negocio": _fact("certificado_bomberos.direccion_negocio", "C. Loiza 500, San Juan", "doc-bomb"),
            "certificacion_crim.fecha_vencimiento": _fact("certificacion_crim.fecha_vencimiento", "2026-11-30", "doc-crim"),
            "certificacion_crim.entidad_emisora": _fact("certificacion_crim.entidad_emisora", "Centro de Recaudacion de Ingresos Municipales", "doc-crim"),
            "certificacion_asume.fecha_vencimiento": _fact("certificacion_asume.fecha_vencimiento", "2026-10-15", "doc-asume"),
            "certificacion_asume.entidad_emisora": _fact("certificacion_asume.entidad_emisora", "ASUME", "doc-asume"),
            "certificado_bomberos.fecha_vencimiento": _fact("certificado_bomberos.fecha_vencimiento", "2027-01-15", "doc-bomb"),
            "certificado_bomberos.entidad_emisora": _fact("certificado_bomberos.entidad_emisora", "Negociado del Cuerpo de Bomberos de Puerto Rico", "doc-bomb"),
            "escritura_titularidad.catastro": _fact("escritura_titularidad.catastro", "123-456-789-01", "doc-esc"),
            "certificacion_crim.catastro": _fact("certificacion_crim.catastro", "12345678901", "doc-crim"),
            "plano_distribucion.profesional_autorizado": _fact("plano_distribucion.profesional_autorizado", "Arq. Ana Ruiz", "doc-plano"),
            "plano_distribucion.numero_licencia": _fact("plano_distribucion.numero_licencia", "12345", "doc-plano"),
        },
        document_types=list(docs.keys()),
        document_ids_by_type=docs,
        document_bands={code: "alta" for code in docs},
        profile={
            "forma_juridica": "entidad_juridica",
            "tenencia": "dueno",
            "categoria_uso": "comercio_general",
            "acceso_publico": False,
            "radica_representante": False,
        },
        case={"filing_date": "2026-03-01", "catastro": "12345678901"},
    )


def test_a_complete_application_produces_no_findings():
    results = evaluate_case(SEED_RULES, complete_case_context())
    findings = [r for r in results if r.status == HALLAZGO_IDENTIFICADO]

    assert not findings, [
        (f.rule_code, f.explanation) for f in findings
    ]
    assert summarize(results)[SIN_HALLAZGOS] > 0


def test_a_missing_certification_is_found_and_names_the_inventory():
    ctx = complete_case_context()
    ctx.document_types.remove("certificado_bomberos")
    del ctx.document_ids_by_type["certificado_bomberos"]

    results = evaluate_case(SEED_RULES, ctx)
    by_code = {r.rule_code: r for r in results}

    assert by_code["P-05"].status == HALLAZGO_IDENTIFICADO
    assert by_code["P-05"].evidence_ids  # the inventory backs the absence
    # Validity of an absent document is not evaluated at all.
    assert "V-03" not in by_code


def test_an_expired_certification_is_found():
    ctx = complete_case_context()
    ctx.facts["certificacion_crim.fecha_vencimiento"] = _fact(
        "certificacion_crim.fecha_vencimiento", "2025-06-30", "doc-crim"
    )

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    assert by_code["V-01"].status == HALLAZGO_IDENTIFICADO


def test_an_illegible_expiry_escalates_rather_than_accusing():
    ctx = complete_case_context()
    ctx.facts["certificacion_crim.fecha_vencimiento"] = _fact(
        "certificacion_crim.fecha_vencimiento", "ilegible", "doc-crim"
    )

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    assert by_code["V-01"].status == REQUIERE_CRITERIO


def test_a_substantively_different_name_is_a_finding_citing_both_documents():
    ctx = complete_case_context()
    ctx.facts["patente_municipal.nombre_solicitante"] = _fact(
        "patente_municipal.nombre_solicitante", "Ferreteria Marte LLC", "doc-pat"
    )

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    finding = by_code["C-01"]

    assert finding.status == HALLAZGO_IDENTIFICADO
    assert len(set(finding.evidence_ids)) >= 2
    assert "Panaderia Lopez Inc." in finding.explanation
    assert "Ferreteria Marte LLC" in finding.explanation


def test_a_plausible_name_variant_escalates_instead_of_accusing():
    """
    The married-name case, end to end through the real ruleset. This is the
    single most important behaviour in the consistency family.
    """
    ctx = complete_case_context()
    ctx.profile["forma_juridica"] = "persona_natural"
    ctx.facts["patente_municipal.nombre_solicitante"] = _fact(
        "patente_municipal.nombre_solicitante", "Maria Rivera Colon", "doc-pat"
    )
    ctx.facts["certificacion_crim.nombre_solicitante"] = _fact(
        "certificacion_crim.nombre_solicitante", "Maria Rivera de Santiago", "doc-crim"
    )

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    assert by_code["C-02"].status == REQUIERE_CRITERIO


def test_unanswered_profile_escalates_the_conditional_rules():
    ctx = complete_case_context()
    ctx.profile = {}

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    for code in ("P-06", "P-09", "P-10"):
        assert by_code[code].status == REQUIERE_CRITERIO
        assert by_code[code].reason_code == "aplicabilidad_indeterminada"


def test_unclassified_documents_escalate_and_never_accuse():
    ctx = complete_case_context()
    ctx.document_types.append("desconocido")
    ctx.document_ids_by_type["desconocido"] = "doc-???"

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}
    assert by_code["P-11"].status == REQUIERE_CRITERIO


def test_zoning_rule_stays_off_until_the_gis_wrapper_lands():
    """
    A rule that escalates on every case teaches reviewers to ignore escalations.
    A-01 ships disabled and is enabled with one UPDATE when it can be answered.
    """
    zoning = next(r for r in SEED_RULES if r["code"] == "A-01")
    assert zoning["enabled"] is False
    assert "A-01" not in {r.rule_code for r in evaluate_case(SEED_RULES, complete_case_context())}
