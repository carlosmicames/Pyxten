"""
The requerimiento de subsanacion.

This is the deliverable, so these tests are about one boundary above all others:
the model writes prose around findings the engine already decided, and it cannot
add one, drop one, change what one says, or cite a page that is not evidence.
"""
import re

import pytest

from app.reviewer import notice, notice_pdf


def _check_row(
    check_id,
    rule_code,
    status="hallazgo_identificado",
    citations=None,
    severity="grave",
    reason_code=None,
):
    return {
        "id": check_id,
        "case_id": "case-1",
        "rule_id": f"rule-{rule_code}",
        "family": "presencia",
        "status": status,
        "band": "alta",
        "evidence_ids": ["doc-pat"],
        "citations": citations
        if citations is not None
        else [
            {
                "field_key": "documento.patente_municipal",
                "document_id": "doc-pat",
                "page": 3,
                "value": "Panaderia Lopez Inc.",
                "band": "alta",
            }
        ],
        "explanation": f"Explicacion determinista de {rule_code}.",
        "reason_code": reason_code,
        "evaluated_at": "2026-03-01T10:00:00Z",
        "rules": {
            "code": rule_code,
            "title": f"Titulo de {rule_code}",
            "citation": "Reglamento Conjunto 2023",
            "severity": severity,
        },
    }


CASE = {
    "id": "case-1",
    "case_number": "SJ-2026-0001",
    "applicant_name": "Panaderia Lopez Inc.",
    "property_address": "Calle Loiza 500",
    "catastro": "123-456-789-01",
    "ruleset_version_id": "rs-1",
}


@pytest.fixture()
def seeded(reviewer_ctx):
    reviewer_ctx.db.tables["compliance_checks"] = [
        _check_row("chk-1", "P-05"),
        _check_row("chk-2", "V-01", severity="moderada"),
        _check_row("chk-3", "P-11", status="requiere_criterio", reason_code="banda_baja"),
        _check_row("chk-4", "P-01", status="sin_hallazgos"),
    ]
    reviewer_ctx.db.tables["case_documents"] = [
        {
            "id": "doc-pat",
            "case_id": "case-1",
            "filename": "patente.pdf",
            "doc_type": "patente_municipal",
        }
    ]
    # The taxonomy comes from the case's ruleset, not from code.
    reviewer_ctx.db.tables["document_types"] = [
        {
            "ruleset_id": "rs-1",
            "code": "patente_municipal",
            "name": "Patente Municipal",
            "description": "",
            "sort_order": 20,
        }
    ]
    return reviewer_ctx


# =============================================================================
# What goes in
# =============================================================================

def test_only_identified_findings_are_eligible(seeded):
    findings, pending = notice.collect(seeded, "case-1")

    assert {f.rule_code for f in findings} == {"P-05", "V-01"}
    # A check the system could not determine is not a deficiency to serve.
    assert [p["rule_code"] for p in pending] == ["P-11"]


def test_findings_are_ordered_gravest_first(seeded):
    findings, _ = notice.collect(seeded, "case-1")
    assert [f.severity for f in findings] == ["grave", "moderada"]


def test_a_case_with_no_findings_produces_no_notice(reviewer_ctx):
    reviewer_ctx.db.tables["compliance_checks"] = [
        _check_row("chk-1", "P-01", status="sin_hallazgos")
    ]
    reviewer_ctx.db.tables["case_documents"] = []

    result = notice.build(reviewer_ctx, "case-1", CASE)
    assert "error" in result
    assert "No hay hallazgos" in result["error"]


def test_pending_checks_are_named_when_a_notice_cannot_be_drafted(reviewer_ctx):
    """A reviewer needs to know what to resolve, not just that nothing happened."""
    reviewer_ctx.db.tables["compliance_checks"] = [
        _check_row("chk-1", "V-03", status="requiere_criterio", reason_code="banda_baja")
    ]
    reviewer_ctx.db.tables["case_documents"] = []

    result = notice.build(reviewer_ctx, "case-1", CASE)
    assert "requieren criterio" in result["error"]
    assert result["pendientes"][0]["rule_code"] == "V-03"


# =============================================================================
# The model cannot invent, drop, or misattribute a finding
# =============================================================================

def _stub_model(monkeypatch, payload, model="claude-opus-5"):
    class FakeBlock:
        type = "text"

        def __init__(self, text):
            self.text = text

    class FakeResponse:
        stop_reason = "end_turn"

        def __init__(self, text):
            self.content = [FakeBlock(text)]

    class FakeMessages:
        def create(self, **kwargs):
            import json as _json

            return FakeResponse(_json.dumps(payload))

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(notice, "_client", lambda: FakeClient())
    monkeypatch.setattr(
        notice, "get_settings", lambda: type("S", (), {"reviewer_model": model, "anthropic_api_key": "k"})()
    )


def test_a_finding_the_model_invented_is_discarded(seeded, monkeypatch):
    """
    The model returns a rule code nobody sent it. It does not reach the notice.
    """
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": "Parrafo real.", "subsanacion": "Presente el documento."},
            {"rule_code": "X-99", "parrafo": "Hallazgo inventado.", "subsanacion": "Nada."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    codes = {h["rule_code"] for h in result["body"]["hallazgos"]}

    assert codes == {"P-05", "V-01"}
    assert "X-99" not in codes


def test_a_finding_the_model_omitted_still_appears(seeded, monkeypatch):
    """
    Silence is not a way to drop a deficiency. The omitted finding gets the
    engine's own deterministic text instead.
    """
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": "Solo este.", "subsanacion": "Presente el documento."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    by_code = {h["rule_code"]: h for h in result["body"]["hallazgos"]}

    assert set(by_code) == {"P-05", "V-01"}
    assert by_code["V-01"]["generado"] == "sistema"
    assert "Explicacion determinista de V-01" in by_code["V-01"]["parrafo"]


def test_prose_citing_a_page_that_is_not_evidence_is_rejected(seeded, monkeypatch):
    """
    The control that matters most. The finding cites page 3; the model writes
    page 11. That paragraph is discarded, with the reason recorded.
    """
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {
                "rule_code": "P-05",
                "parrafo": "Segun consta en la pagina 11 del expediente.",
                "subsanacion": "Presente el certificado.",
            },
            {"rule_code": "V-01", "parrafo": "Texto valido.", "subsanacion": "Presente."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    by_code = {h["rule_code"]: h for h in result["body"]["hallazgos"]}

    assert by_code["P-05"]["generado"] == "sistema"
    assert "pagina 11" in by_code["P-05"]["descartado_por"]
    assert by_code["V-01"]["generado"] == "modelo"


def test_prose_citing_a_page_that_is_evidence_is_kept(seeded, monkeypatch):
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": "Consta en la pag. 3.", "subsanacion": "Presente."},
            {"rule_code": "V-01", "parrafo": "Texto.", "subsanacion": "Presente."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    by_code = {h["rule_code"]: h for h in result["body"]["hallazgos"]}
    assert by_code["P-05"]["generado"] == "modelo"


@pytest.mark.parametrize(
    "bad_text",
    [
        "El expediente esta NON-COMPLIANT con el reglamento.",
        "La solicitud es COMPLIANT en este aspecto.",
        "Se determino con 87% de certeza que falta el documento.",
    ],
)
def test_forbidden_language_is_rejected(seeded, monkeypatch, bad_text):
    """
    Neither of the banned words, nor a confidence percentage, may reach a
    document a municipality signs.
    """
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": bad_text, "subsanacion": "Presente."},
            {"rule_code": "V-01", "parrafo": "Texto.", "subsanacion": "Presente."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    by_code = {h["rule_code"]: h for h in result["body"]["hallazgos"]}
    assert by_code["P-05"]["generado"] == "sistema"


def test_the_whole_document_is_free_of_forbidden_language(seeded, monkeypatch):
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion normal.",
        "cierre": "Cierre normal.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": "Texto.", "subsanacion": "Presente."},
            {"rule_code": "V-01", "parrafo": "Texto.", "subsanacion": "Presente."},
        ],
    })

    import json

    rendered = json.dumps(notice.build(seeded, "case-1", CASE)["body"]).upper()
    assert "NON-COMPLIANT" not in rendered
    assert not re.search(r"\bCOMPLIANT\b", rendered)
    assert not re.search(r"\b\d{1,3}\s?%", rendered)


def test_citations_are_appended_by_the_system_not_written_by_the_model(seeded, monkeypatch):
    _stub_model(monkeypatch, {
        "introduccion": "Introduccion.",
        "cierre": "Cierre.",
        "hallazgos": [
            {"rule_code": "P-05", "parrafo": "Texto.", "subsanacion": "Presente."},
            {"rule_code": "V-01", "parrafo": "Texto.", "subsanacion": "Presente."},
        ],
    })

    result = notice.build(seeded, "case-1", CASE)
    evidence = result["body"]["hallazgos"][0]["evidencia"]

    assert evidence == [
        {"documento": "Patente Municipal", "pagina": 3, "valor": "Panaderia Lopez Inc."}
    ]


def test_an_api_failure_still_produces_a_complete_notice(seeded, monkeypatch):
    """
    A municipal office cannot be blocked from issuing a requerimiento because a
    vendor is down. Every finding falls back to the engine's own explanation.
    """
    monkeypatch.setattr(notice, "_client", lambda: None)

    result = notice.build(seeded, "case-1", CASE)
    hallazgos = result["body"]["hallazgos"]

    assert len(hallazgos) == 2
    assert all(h["generado"] == "sistema" for h in hallazgos)
    assert all(h["parrafo"] for h in hallazgos)
    assert result["model_used"] is None


# =============================================================================
# Drafts, approval, and the absence of a send path
# =============================================================================

def test_a_new_notice_is_always_a_draft(seeded, monkeypatch):
    monkeypatch.setattr(notice, "_client", lambda: None)
    result = notice.build(seeded, "case-1", CASE)

    assert result["status"] == "borrador"
    assert result["approved_by"] is None if "approved_by" in result else True


def test_versions_increment_rather_than_overwrite(seeded, monkeypatch):
    monkeypatch.setattr(notice, "_client", lambda: None)

    first = notice.build(seeded, "case-1", CASE)
    second = notice.build(seeded, "case-1", CASE)

    assert first["version"] == 1
    assert second["version"] == 2
    assert len(seeded.db.rows("requerimientos")) == 2


def test_approval_records_who_and_when(seeded, monkeypatch):
    monkeypatch.setattr(notice, "_client", lambda: None)
    draft = notice.build(seeded, "case-1", CASE)

    approved = notice.approve(seeded, draft["id"])

    assert approved["status"] == "aprobado"
    assert approved["approved_by"] == str(seeded.user_id)
    assert approved["approved_at"]
    assert "requerimiento_approved" in seeded.db.audit_types()


def test_approving_twice_is_refused(seeded, monkeypatch):
    monkeypatch.setattr(notice, "_client", lambda: None)
    draft = notice.build(seeded, "case-1", CASE)
    notice.approve(seeded, draft["id"])

    assert "error" in notice.approve(seeded, draft["id"])


def test_there_is_no_send_path_in_the_notice_module():
    import inspect

    source = inspect.getsource(notice)
    for term in ("smtp", "sendgrid", "send_email", "mailgun", "twilio", "recipient"):
        assert term not in source.lower()


# =============================================================================
# The PDF
# =============================================================================

def _rendered(seeded, monkeypatch, status="borrador"):
    monkeypatch.setattr(notice, "_client", lambda: None)
    draft = notice.build(seeded, "case-1", CASE)
    draft["status"] = status
    return notice_pdf.render(draft)


def test_pdf_renders(seeded, monkeypatch):
    pdf = _rendered(seeded, monkeypatch)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 2000


def test_a_unicode_font_is_available_so_accents_survive():
    """
    The applicant-side PDFs drop accents to dodge encoding problems. A document
    a municipality serves cannot. Vera ships inside reportlab, so this holds
    wherever the API runs.
    """
    assert notice_pdf._register_fonts() is True


def test_a_draft_is_watermarked_and_an_approved_notice_is_not(seeded, monkeypatch):
    draft = _rendered(seeded, monkeypatch, status="borrador")
    approved = _rendered(seeded, monkeypatch, status="aprobado")

    # The watermark is drawn text, so the draft is measurably larger.
    assert len(draft) > len(approved)


def test_markup_in_a_value_cannot_break_the_document(seeded, monkeypatch):
    """Model and applicant text both reach paragraph markup; both are escaped."""
    seeded.db.tables["compliance_checks"][0]["citations"][0]["value"] = "<b>&raro</b>"
    pdf = _rendered(seeded, monkeypatch)
    assert pdf.startswith(b"%PDF-")
