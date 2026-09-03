"""
Fact extraction and the end-to-end case run.

The band logic is the substance here: it is derived from whether two independent
views of the document agreed, and no model is asked how sure it is.
"""
import re

import pytest

from app.reviewer.extraction import (
    FIELD_SPECS,
    ExtractedFact,
    expected_field_keys,
    extract_document,
)
from app.reviewer.pdf_text import analyze_pdf
from tests.stubs import blank_pdf, make_pdf
from tests.test_seed_rules import MIGRATION, SEED_RULES


# =============================================================================
# The extraction contract matches the rules
# =============================================================================

def _field_keys_referenced_by_rules():
    """
    Every `<doc_type>.<field>` the seeded conditions read.

    Excludes `case.*` and `profile.*`, which come from the case record rather
    than from a document.
    """
    text = MIGRATION.read_text(encoding="utf-8")
    found = set(re.findall(r'"(?:field|left|right)":\s*"([a-z_]+\.[a-z_]+)"', text))
    return {k for k in found if not k.startswith(("case.", "profile."))}


def test_every_field_a_rule_reads_can_be_extracted():
    """
    Closes the loop between migration 007 and the extractor. Adding a rule that
    reads a new field fails here until extraction knows how to find it - which
    is better than the rule silently escalating on every real case forever.
    """
    referenced = _field_keys_referenced_by_rules()
    extractable = expected_field_keys()

    missing = referenced - extractable
    assert not missing, f"rules read fields extraction cannot produce: {sorted(missing)}"


def test_no_extraction_effort_is_wasted_on_fields_no_rule_reads():
    """
    The reverse direction is a warning, not a failure: extracting a field early
    is fine, but it costs tokens on every document, so it should be deliberate.
    """
    unused = expected_field_keys() - _field_keys_referenced_by_rules()
    # Currently every extracted field is read by at least one rule.
    assert unused == set(), f"extracted but unused: {sorted(unused)}"


def test_desconocido_has_no_field_spec():
    """Nothing is extracted from a document we could not identify."""
    assert "desconocido" not in FIELD_SPECS


# =============================================================================
# Band derivation
# =============================================================================

@pytest.fixture()
def stub_views(monkeypatch):
    """
    Replace the two model calls with scripted answers. The first call is the
    text view, the second is the image view.
    """
    from app.reviewer import extraction

    monkeypatch.setattr(extraction, "_client", lambda: object())
    calls = {"answers": [], "index": 0}

    def fake_ask(client, model, content, specs):
        index = calls["index"]
        calls["index"] += 1
        if index < len(calls["answers"]):
            return calls["answers"][index]
        return None

    monkeypatch.setattr(extraction, "_ask", fake_ask)
    return calls


def _answer(**fields):
    return {
        "campos": [
            {
                "campo": key,
                "encontrado": True,
                "valor": value,
                "pagina": page,
                "cita": "cita de prueba",
            }
            for key, (value, page) in fields.items()
        ]
    }


def _crim_pdf():
    return make_pdf([
        "CERTIFICACION DEL CENTRO DE RECAUDACION DE INGRESOS MUNICIPALES para la "
        "propiedad con numero de catastro indicado a continuacion en este documento",
    ])


def test_agreement_between_two_views_is_the_only_route_to_alta(stub_views):
    stub_views["answers"] = [
        _answer(catastro=("123-456-789-01", 1)),
        _answer(catastro=("123-456-789-01", 1)),
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    catastro = next(f for f in facts if f.field_key.endswith(".catastro"))
    assert catastro.band == "alta"
    assert catastro.status == "extraido"
    assert catastro.source_page == 1


def test_agreement_is_judged_after_normalization(stub_views):
    """`123-456-789-01` and `12345678901` are the same parcel."""
    stub_views["answers"] = [
        _answer(catastro=("123-456-789-01", 1)),
        _answer(catastro=("12345678901", 1)),
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    assert next(f for f in facts if f.field_key.endswith(".catastro")).band == "alta"


def test_disagreement_is_contradictory_and_records_both_readings(stub_views):
    stub_views["answers"] = [
        _answer(catastro=("123-456-789-01", 1)),
        _answer(catastro=("999-888-777-66", 1)),
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    catastro = next(f for f in facts if f.field_key.endswith(".catastro"))
    assert catastro.band == "baja"
    assert catastro.status == "contradictorio"
    assert "123-456-789-01" in catastro.note and "999-888-777-66" in catastro.note


def test_one_view_only_reaches_media_not_alta(stub_views):
    stub_views["answers"] = [_answer(catastro=("123-456-789-01", 1)), {"campos": []}]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    assert next(f for f in facts if f.field_key.endswith(".catastro")).band == "media"


def test_a_scan_has_no_text_view_so_cannot_reach_alta(stub_views):
    stub_views["answers"] = [_answer(catastro=("123-456-789-01", 1))]
    content = blank_pdf(2)
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    catastro = next(f for f in facts if f.field_key.endswith(".catastro"))
    assert catastro.band == "media"
    assert catastro.note == "solo_vista_imagen"


def test_a_field_neither_view_found_is_evidence_unavailable(stub_views):
    stub_views["answers"] = [{"campos": []}, {"campos": []}]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    assert all(f.status == "evidencia_no_disponible" for f in facts)
    assert all(f.band == "baja" for f in facts)
    assert all(f.source_page is None for f in facts)


def test_a_value_without_a_page_is_not_a_fact(stub_views):
    """
    A reading that cannot be cited is discarded rather than stored. Keeping it
    would let it agree with the other view and reach a high band, and a finding
    that cannot point at a page cannot be defended.
    """
    stub_views["answers"] = [
        {"campos": [{"campo": "catastro", "encontrado": True, "valor": "123-456-789-01",
                     "pagina": 0, "cita": ""}]},
        {"campos": []},
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    assert next(f for f in facts if f.field_key.endswith(".catastro")).status == "evidencia_no_disponible"


def test_dates_are_parsed_into_a_sortable_value(stub_views):
    stub_views["answers"] = [
        _answer(fecha_vencimiento=("15 de enero de 2027", 2)),
        _answer(fecha_vencimiento=("2027-01-15", 2)),
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    fecha = next(f for f in facts if f.field_key.endswith(".fecha_vencimiento"))
    assert fecha.band == "alta"          # spelled and numeric forms agree
    assert fecha.value_date == "2027-01-15"
    assert fecha.value_text == "15 de enero de 2027"   # transcription preserved


def test_missing_api_key_yields_unavailable_facts_not_a_crash(monkeypatch):
    from app.reviewer import extraction

    monkeypatch.setattr(extraction, "_client", lambda: None)
    content = _crim_pdf()
    facts, error = extract_document(analyze_pdf(content), content, "certificacion_crim")

    assert error and "ANTHROPIC_API_KEY" in error
    assert facts and all(f.status == "evidencia_no_disponible" for f in facts)


def test_unknown_document_type_extracts_nothing(stub_views):
    content = _crim_pdf()
    facts, error = extract_document(analyze_pdf(content), content, "desconocido")
    assert facts == [] and error is None


# =============================================================================
# Facts flow through to the rules
# =============================================================================

def test_extracted_facts_drive_the_rules_end_to_end(stub_views):
    """
    The join between the two halves of Phase 2: a fact extracted here is keyed
    exactly as the seeded rules expect, so an expired certification produces a
    finding without anything in between translating names.
    """
    from app.reviewer.rules import Context, Fact, evaluate_case

    stub_views["answers"] = [
        _answer(fecha_vencimiento=("2025-06-30", 1),
                entidad_emisora=("Centro de Recaudacion de Ingresos Municipales", 1)),
        _answer(fecha_vencimiento=("2025-06-30", 1),
                entidad_emisora=("Centro de Recaudacion de Ingresos Municipales", 1)),
    ]
    content = _crim_pdf()
    facts, _ = extract_document(analyze_pdf(content), content, "certificacion_crim")

    ctx = Context(
        facts={
            f.field_key: Fact(
                field_key=f.field_key,
                value_text=f.value_text,
                value_date=f.value_date,
                document_id="doc-crim",
                source_page=f.source_page,
                band=f.band,
                status=f.status,
            )
            for f in facts
            if f.status == "extraido"
        },
        document_types=["certificacion_crim"],
        document_ids_by_type={"certificacion_crim": "doc-crim"},
        document_bands={"certificacion_crim": "alta"},
        case={"filing_date": "2026-03-01"},
    )

    by_code = {r.rule_code: r for r in evaluate_case(SEED_RULES, ctx)}

    assert by_code["V-01"].status == "hallazgo_identificado"   # expired
    assert by_code["V-08"].status == "sin_hallazgos"           # issued by CRIM


def test_extracted_fact_row_shape_satisfies_the_evidence_constraint():
    """
    Mirrors extracted_facts_evidence_required: a row claiming `extraido` names
    a document and a page.
    """
    located = ExtractedFact(
        "certificacion_crim.catastro", "123-456-789-01", None, 2, "alta", "extraido"
    ).as_row("case-1", "org-1", "doc-1")

    assert located["status"] == "extraido"
    assert located["document_id"] and located["source_page"]

    absent = ExtractedFact(
        "certificacion_crim.catastro", None, None, None, "baja", "evidencia_no_disponible"
    ).as_row("case-1", "org-1", "doc-1")

    assert absent["source_page"] is None  # allowed, because it does not claim extraido
