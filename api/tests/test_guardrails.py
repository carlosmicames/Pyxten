"""
The guardrails, as executable tests.

A guardrail that lives only in a specification erodes over months of edits. Each
one below is the same rule, written so CI can fail on it.
"""
import ast
import inspect
import re
from pathlib import Path

import pytest

REVIEWER_PACKAGE = Path(__file__).resolve().parents[1] / "app" / "reviewer"
REVIEWER_ROUTER = Path(__file__).resolve().parents[1] / "app" / "routers" / "reviewer.py"


def reviewer_files():
    return list(REVIEWER_PACKAGE.glob("*.py")) + [REVIEWER_ROUTER]


def reviewer_sources():
    """Raw file text, docstrings and all."""
    return {path.name: path.read_text(encoding="utf-8") for path in reviewer_files()}


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    """Remove docstrings so a rule about code is not tripped by a comment about it."""
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", None)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return tree


def reviewer_code():
    """
    The reviewer path as executable code only.

    Comments are dropped by the parser and docstrings are removed above, so these
    guardrail tests assert what the program does rather than how it is described.
    String literals are kept - what the software says to a user is exactly the
    thing several of these rules are about.
    """
    result = {}
    for path in reviewer_files():
        tree = _strip_docstrings(ast.parse(path.read_text(encoding="utf-8")))
        result[path.name] = ast.unparse(tree)
    return result


# =============================================================================
# Anthropic only on the reviewer path
# =============================================================================

def test_reviewer_path_never_imports_openai():
    for name, code in reviewer_code().items():
        assert "openai" not in code.lower(), (
            f"{name} references OpenAI in code; the reviewer path is Anthropic-only"
        )


def test_classifier_uses_anthropic():
    from app.reviewer import classifier

    source = inspect.getsource(classifier)
    assert "import anthropic" in source


# =============================================================================
# No confidence percentages anywhere on the reviewer path
# =============================================================================

def test_no_numeric_confidence_in_reviewer_code():
    """
    The model is never asked how confident it is, and no numeric score is stored
    or returned. Bands are derived from signals we can check ourselves.
    """
    banned = re.compile(r"confidence\s*[\'\":=]", re.IGNORECASE)
    for name, code in reviewer_code().items():
        assert not banned.search(code), f"{name} appears to carry a confidence score"


def test_classifier_schema_does_not_request_confidence():
    from app.reviewer.classifier import _RESULT_SCHEMA

    keys = set(_RESULT_SCHEMA["properties"].keys())
    assert "confidence" not in keys
    assert "score" not in keys
    assert "probability" not in keys


# =============================================================================
# Exact decision-state labels; the forbidden words never appear
# =============================================================================

def test_forbidden_compliance_words_absent():
    for name, code in reviewer_code().items():
        upper = code.upper()
        assert "NON-COMPLIANT" not in upper, f"{name} contains NON-COMPLIANT"
        assert not re.search(r"\bCOMPLIANT\b", upper), f"{name} contains COMPLIANT"


# =============================================================================
# Bands are computed, never asked for
# =============================================================================

@pytest.mark.parametrize("band", ["alta", "media", "baja"])
def test_only_the_three_bands_exist(band):
    from app.reviewer import classifier

    source = inspect.getsource(classifier)
    assert f'"{band}"' in source


def test_scanned_documents_never_reach_the_highest_band(monkeypatch):
    """
    A scan is classified from page images with no second independent view, so by
    the band definition it can be `media` at best - never `alta`.
    """
    from app.reviewer import classifier
    from tests.stubs import blank_pdf

    monkeypatch.setattr(classifier, "_client", lambda: object())
    monkeypatch.setattr(
        classifier,
        "_ask",
        lambda *_args, **_kwargs: {
            "doc_type": "escritura_propiedad",
            "evidence_page": 1,
            "evidence_quote": "ESCRITURA DE COMPRAVENTA",
        },
    )

    content = blank_pdf(3)
    analysis = classifier_analysis(content)
    result = classifier.classify(analysis, "escaneo.pdf", content)

    assert result.doc_type == "escritura_propiedad"
    assert result.band == "media"
    assert "pase_unico" in result.reason


def test_disagreeing_views_produce_no_label(monkeypatch):
    """
    When the two views disagree the system does not pick a winner. It records
    `desconocido` with a reason naming both candidates, and a human decides.
    """
    from app.reviewer import classifier
    from tests.stubs import make_pdf

    answers = iter(
        [
            {"doc_type": "escritura_propiedad", "evidence_page": 1, "evidence_quote": "a"},
            {"doc_type": "plano_mensura", "evidence_page": 2, "evidence_quote": "b"},
        ]
    )

    monkeypatch.setattr(classifier, "_client", lambda: object())
    monkeypatch.setattr(classifier, "_ask", lambda *_a, **_k: next(answers))

    content = make_pdf(
        [
            "ESCRITURA DE COMPRAVENTA otorgada ante notario publico en San Juan "
            "Puerto Rico con fecha del quince de enero de dos mil veinticuatro",
            "PLANO DE MENSURA certificado por agrimensor licenciado colegiado "
            "numero mil doscientos treinta y cuatro del Colegio de Ingenieros",
        ]
    )
    analysis = classifier_analysis(content)
    result = classifier.classify(analysis, "mixto.pdf", content)

    assert result.doc_type == "desconocido"
    assert result.band == "baja"
    assert "vistas_contradictorias" in result.reason


def test_out_of_catalog_code_is_rejected():
    """The catalog is the authority, not the model."""
    from app.reviewer.classifier import _normalize

    code, page, quote = _normalize(
        {"doc_type": "inventado_por_el_modelo", "evidence_page": 3, "evidence_quote": "x"}
    )
    assert code is None


def test_missing_api_key_degrades_to_unknown_not_a_guess(monkeypatch):
    from app.reviewer import classifier
    from tests.stubs import make_pdf

    monkeypatch.setattr(classifier, "_client", lambda: None)

    content = make_pdf(["texto cualquiera de prueba para el documento"])
    result = classifier.classify(classifier_analysis(content), "x.pdf", content)

    assert result.doc_type == "desconocido"
    assert result.band == "baja"
    assert result.ok is False


# =============================================================================
# Nothing is sent to an applicant
# =============================================================================

def test_no_send_path_exists_on_the_reviewer_side():
    banned = ("smtplib", "sendgrid", "send_email", "sendmail", "twilio", "mailgun")
    for name, code in reviewer_code().items():
        lowered = code.lower()
        for term in banned:
            assert term not in lowered, f"{name} references {term}"


# =============================================================================
# The audit trail cannot be edited from application code
# =============================================================================

def test_audit_module_offers_no_update_or_delete():
    from app.reviewer import audit

    exported = {name for name in dir(audit) if not name.startswith("_")}
    assert "record" in exported
    for forbidden in ("update", "delete", "edit", "remove"):
        assert forbidden not in exported


def test_migration_makes_audit_events_append_only():
    migration = (
        Path(__file__).resolve().parents[2] / "migrations" / "005_reviewer_core.sql"
    ).read_text(encoding="utf-8")

    assert "audit_events_append_only" in migration
    assert "REVOKE UPDATE, DELETE ON audit_events" in migration
    # No UPDATE or DELETE policy should exist for the table.
    assert "audit_events FOR UPDATE" not in migration
    assert "audit_events FOR DELETE" not in migration


def test_migration_requires_evidence_for_extracted_facts():
    migration = (
        Path(__file__).resolve().parents[2] / "migrations" / "005_reviewer_core.sql"
    ).read_text(encoding="utf-8")

    assert "extracted_facts_evidence_required" in migration
    assert "source_page IS NOT NULL" in migration


def test_migration_freezes_the_ruleset_stamp():
    migration = (
        Path(__file__).resolve().parents[2] / "migrations" / "005_reviewer_core.sql"
    ).read_text(encoding="utf-8")

    assert "cases_freeze_ruleset" in migration
    assert "ruleset_version_id is immutable" in migration


# -----------------------------------------------------------------------------

def classifier_analysis(content: bytes):
    from app.reviewer.pdf_text import analyze_pdf

    return analyze_pdf(content)
