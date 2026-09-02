"""
Intake: hashing, page indexing, deduplication, and the audit trail it writes.
"""
import pytest
from fastapi import HTTPException

from tests.stubs import blank_pdf, make_pdf


# =============================================================================
# PDF reading
# =============================================================================

def test_extracts_text_page_by_page():
    from app.reviewer.pdf_text import analyze_pdf

    content = make_pdf(
        [
            "CERTIFICACION DE DEUDA emitida por el Centro de Recaudacion de "
            "Ingresos Municipales para la propiedad indicada a continuacion",
            "Segunda pagina con contenido adicional suficiente para superar el "
            "umbral minimo de caracteres que exige el extractor de texto",
        ]
    )
    analysis = analyze_pdf(content)

    assert analysis.page_count == 2
    assert len(analysis.pages) == 2
    assert analysis.pages[0].page_no == 1  # 1-indexed, like a person cites pages
    assert analysis.ocr_status == "texto_incrustado"
    assert analysis.readable is True
    assert "CERTIFICACION" in analysis.pages[0].text


def test_pages_without_text_are_reported_as_scans():
    from app.reviewer.pdf_text import analyze_pdf

    analysis = analyze_pdf(blank_pdf(3))

    assert analysis.page_count == 3
    assert analysis.ocr_status == "sin_texto"
    assert analysis.readable is False
    assert all(p.extraction_method == "ninguno" for p in analysis.pages)


def test_unparseable_bytes_report_an_error_rather_than_raising():
    from app.reviewer.pdf_text import analyze_pdf

    analysis = analyze_pdf(b"%PDF-1.4 this is not really a pdf")

    assert analysis.ocr_status == "error"
    assert analysis.error is not None
    assert analysis.sha256  # hashing still succeeded


def test_hash_is_stable_and_content_addressed():
    from app.reviewer.pdf_text import analyze_pdf, sha256_of

    content = make_pdf(["contenido de prueba para verificar el hash del documento"])
    assert analyze_pdf(content).sha256 == sha256_of(content)
    assert len(sha256_of(content)) == 64


def test_combined_text_labels_each_page_so_citations_resolve():
    from app.reviewer.pdf_text import analyze_pdf

    analysis = analyze_pdf(
        make_pdf(
            [
                "Primera pagina del documento con texto suficiente para ser contada "
                "como una pagina con contenido legible por el extractor",
                "Segunda pagina del documento con texto suficiente para ser contada "
                "como una pagina con contenido legible por el extractor",
            ]
        )
    )
    combined = analysis.combined_text()

    assert "--- Pagina 1 ---" in combined
    assert "--- Pagina 2 ---" in combined


# =============================================================================
# Upload validation
# =============================================================================

def test_rejects_non_pdf():
    from app.reviewer.intake import validate_upload

    with pytest.raises(HTTPException) as exc:
        validate_upload("foto.jpg", b"\xff\xd8\xff\xe0 jpeg bytes")
    assert "no es un PDF" in str(exc.value.detail)


def test_rejects_empty_file():
    from app.reviewer.intake import validate_upload

    with pytest.raises(HTTPException):
        validate_upload("vacio.pdf", b"")


def test_rejects_oversized_file():
    from app.reviewer.intake import MAX_FILE_BYTES, validate_upload

    with pytest.raises(HTTPException) as exc:
        validate_upload("enorme.pdf", b"%PDF-" + b"x" * MAX_FILE_BYTES)
    assert "excede el limite" in str(exc.value.detail)


# =============================================================================
# Ingest
# =============================================================================

@pytest.fixture()
def stub_classifier(monkeypatch):
    from app.reviewer import classifier, intake
    from app.reviewer.classifier import Classification

    def fake(analysis, filename, content):
        return Classification(
            doc_type="certificacion_deuda_crim",
            band="alta",
            reason="concordancia: ambas vistas coinciden y el documento tiene texto incrustado",
            evidence_page=1,
        )

    monkeypatch.setattr(intake, "classify", fake)
    return fake


def test_ingest_stores_hashes_pages_and_writes_audit(reviewer_ctx, stub_classifier):
    from app.reviewer.intake import ingest_document

    content = make_pdf(
        [
            "CERTIFICACION NEGATIVA DE DEUDA del CRIM para la propiedad ubicada "
            "en el municipio de San Juan segun los registros vigentes"
        ]
    )
    document = ingest_document(reviewer_ctx, "case-1", "crim.pdf", content)

    assert document["doc_type"] == "certificacion_deuda_crim"
    assert document["classification_band"] == "alta"
    assert document["doc_type_source"] == "modelo"
    assert document["processing_status"] == "listo"
    assert len(document["sha256"]) == 64

    # The bytes went to org-scoped storage before anything was classified.
    bucket, path, size = reviewer_ctx.db.uploads[0]
    assert bucket == "expedientes"
    assert path.startswith(f"{reviewer_ctx.org_id}/case-1/")
    assert size == len(content)

    # Page text was indexed so a citation can later resolve.
    assert len(reviewer_ctx.db.rows("document_pages")) == 1

    # And the whole thing is on the record.
    assert reviewer_ctx.db.audit_types() == ["document_uploaded", "document_classified"]


def test_same_file_twice_in_one_case_is_rejected(reviewer_ctx, stub_classifier):
    from app.reviewer.intake import ingest_document

    content = make_pdf(
        ["Documento identico subido dos veces al mismo expediente para probar el hash"]
    )
    ingest_document(reviewer_ctx, "case-1", "original.pdf", content)

    with pytest.raises(HTTPException) as exc:
        ingest_document(reviewer_ctx, "case-1", "copia.pdf", content)

    assert "ya fue subido" in str(exc.value.detail)
    assert "document_duplicate_rejected" in reviewer_ctx.db.audit_types()


def test_case_number_suggestion_uses_the_office_prefix(reviewer_ctx):
    from app.reviewer.intake import next_case_number

    suggestion = next_case_number(reviewer_ctx)
    assert suggestion.startswith("SJ-")
    assert suggestion.endswith("-0001")


def test_case_number_suggestion_increments(reviewer_ctx):
    from datetime import datetime

    from app.reviewer.intake import next_case_number

    year = datetime.utcnow().year
    reviewer_ctx.db.rows("cases").append(
        {"org_id": reviewer_ctx.org_id, "case_number": f"SJ-{year}-0007"}
    )

    assert next_case_number(reviewer_ctx) == f"SJ-{year}-0008"
