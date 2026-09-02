"""
Intake: taking a PDF off a reviewer's desk and turning it into a case document.

The order of operations matters. The file is hashed and stored before anything
is classified, so a document exists with its evidence intact even if the model
call later fails. Classification then updates a row that is already durable.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.reviewer import audit, taxonomy
from app.reviewer.classifier import classify
from app.reviewer.context import ReviewerContext
from app.reviewer.pdf_text import analyze_pdf

logger = logging.getLogger(__name__)

BUCKET = "expedientes"

# Municipal packages run large; this is per file, not per case.
MAX_FILE_BYTES = 25 * 1024 * 1024

# Number of PDFs accepted in a single upload request.
MAX_FILES_PER_REQUEST = 20

# Cap on page rows written per document. A 600-page plan set does not need every
# page indexed to be classified, and unbounded inserts are a denial-of-service
# waiting to happen.
MAX_PAGES_STORED = 400

_PDF_MAGIC = b"%PDF-"


def _reject(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def validate_upload(filename: str, content: bytes) -> None:
    """Cheap checks before anything is hashed or stored."""
    if not content:
        raise _reject(f"'{filename}' esta vacio.")
    if len(content) > MAX_FILE_BYTES:
        mb = MAX_FILE_BYTES // (1024 * 1024)
        raise _reject(f"'{filename}' excede el limite de {mb} MB.")
    if not content.startswith(_PDF_MAGIC):
        raise _reject(f"'{filename}' no es un PDF valido.")


def ingest_document(
    ctx: ReviewerContext,
    case_id: str,
    filename: str,
    content: bytes,
) -> Dict[str, Any]:
    """
    Store one PDF against a case, index its pages, and classify it.

    Returns the stored document row. Raises only for input the reviewer can fix
    (not a PDF, too large, already uploaded); a classification failure comes back
    as a document with `desconocido` and a reason, which is a valid outcome.
    """
    validate_upload(filename, content)

    analysis = analyze_pdf(content)

    # --- Already in this case? ------------------------------------------------
    existing = ctx.db.select_one(
        "case_documents",
        columns="id,filename",
        filters={"case_id": f"eq.{case_id}", "sha256": f"eq.{analysis.sha256}"},
    )
    if existing:
        audit.record(
            ctx,
            audit.DOCUMENT_DUPLICATE_REJECTED,
            case_id=case_id,
            object_ref=existing["id"],
            payload={"filename": filename, "sha256": analysis.sha256},
        )
        raise _reject(
            f"'{filename}' ya fue subido a este expediente como "
            f"'{existing['filename']}' (mismo contenido)."
        )

    # --- Store the bytes first ------------------------------------------------
    document_id = str(uuid.uuid4())
    storage_path = f"{ctx.org_id}/{case_id}/{document_id}.pdf"
    ctx.db.storage_upload(BUCKET, storage_path, content)

    rows = ctx.db.insert(
        "case_documents",
        {
            "id": document_id,
            "case_id": case_id,
            "org_id": ctx.org_id,
            "filename": filename,
            "doc_type": taxonomy.UNKNOWN,
            "doc_type_source": "pendiente",
            "storage_uri": storage_path,
            "sha256": analysis.sha256,
            "page_count": analysis.page_count,
            "text_char_count": analysis.total_chars,
            "ocr_status": analysis.ocr_status,
            "processing_status": "clasificando",
        },
    )
    document = rows[0]

    audit.record(
        ctx,
        audit.DOCUMENT_UPLOADED,
        case_id=case_id,
        object_ref=document_id,
        payload={
            "filename": filename,
            "sha256": analysis.sha256,
            "page_count": analysis.page_count,
            "ocr_status": analysis.ocr_status,
        },
    )

    _store_pages(ctx, document_id, analysis)

    # --- Classify -------------------------------------------------------------
    result = classify(analysis, filename, content)

    updates = {
        "doc_type": result.doc_type,
        "doc_type_source": "modelo",
        "classification_band": result.band,
        "classification_reason": result.reason,
        "classification_page": result.evidence_page,
        "processing_status": "listo" if result.ok else "error",
        "processing_error": None if result.ok else result.reason,
    }

    updated = ctx.db.update(
        "case_documents",
        filters={"id": f"eq.{document_id}"},
        values=updates,
    )

    audit.record(
        ctx,
        audit.DOCUMENT_CLASSIFIED if result.ok else audit.DOCUMENT_CLASSIFICATION_FAILED,
        case_id=case_id,
        object_ref=document_id,
        payload={
            "doc_type": result.doc_type,
            "band": result.band,
            "reason": result.reason,
            "evidence_page": result.evidence_page,
        },
    )

    return updated[0] if updated else {**document, **updates}


def _store_pages(ctx: ReviewerContext, document_id: str, analysis) -> None:
    """
    Index page text so a citation can later resolve to a specific page.

    Pages with no text are still recorded: knowing page 7 is a scan is itself
    evidence when a check has to report that something could not be read.
    """
    pages: List[Dict[str, Any]] = [
        {
            "document_id": document_id,
            "org_id": ctx.org_id,
            "page_no": page.page_no,
            "text": page.text or None,
            "char_count": page.char_count,
            "extraction_method": page.extraction_method,
        }
        for page in analysis.pages[:MAX_PAGES_STORED]
    ]

    if not pages:
        return

    # Chunked so one very long document does not become a single enormous insert.
    for start in range(0, len(pages), 100):
        try:
            ctx.db.insert(table="document_pages", rows=pages[start : start + 100], returning=False)
        except Exception as exc:
            # Page text is an index over evidence we already stored; losing it
            # degrades citation lookup but must not lose the document.
            logger.error("Failed to store pages for document %s: %s", document_id, exc)
            return


def next_case_number(ctx: ReviewerContext) -> str:
    """
    Suggest the next case number for this office, e.g. `SJ-2026-0007`.

    Advisory only - the reviewer can type their own, and the database's
    (org_id, case_number) uniqueness is what actually prevents collisions.
    """
    from datetime import datetime

    prefix = ctx.org_config.get("case_number_prefix") or (
        ctx.municipality[:2].upper() if ctx.municipality else "EXP"
    )
    year = datetime.utcnow().year

    recent = ctx.db.select(
        "cases",
        columns="case_number",
        filters={"org_id": f"eq.{ctx.org_id}", "case_number": f"like.{prefix}-{year}-%"},
        order="case_number.desc",
        limit=1,
    )

    sequence = 1
    if recent:
        tail = recent[0]["case_number"].rsplit("-", 1)[-1]
        if tail.isdigit():
            sequence = int(tail) + 1

    return f"{prefix}-{year}-{sequence:04d}"


def signed_document_url(ctx: ReviewerContext, document: Dict[str, Any]) -> Optional[str]:
    try:
        return ctx.db.storage_signed_url(BUCKET, document["storage_uri"], expires_in=300)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not sign document %s: %s", document.get("id"), exc)
        return None
