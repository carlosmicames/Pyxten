"""
Reviewer console endpoints.

Mounted under /reviewer. Every route depends on `get_reviewer_context`, so a
user with no organization membership - which is every applicant-side account -
gets a 403 and never sees that these routes exist in any useful sense.

Nothing here sends anything to an applicant. There is no email path, no notify
path, and no outbound call other than to Anthropic for classification.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.reviewer import audit, evaluation, gis, intake, taxonomy
from app.reviewer.context import ReviewerContext, get_reviewer_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviewer", tags=["reviewer"])


# =============================================================================
# Request bodies
# =============================================================================

class CaseCreate(BaseModel):
    case_number: Optional[str] = Field(None, max_length=64)
    permit_type: str = "permiso_unico"
    applicant_name: Optional[str] = Field(None, max_length=300)
    property_address: Optional[str] = Field(None, max_length=500)
    catastro: Optional[str] = Field(None, max_length=64)


class CaseUpdate(BaseModel):
    applicant_name: Optional[str] = Field(None, max_length=300)
    # Answers that decide which rules apply. An unanswered key is never read as
    # "no" - the evaluator returns unknown and the rule escalates.
    profile: Optional[Dict[str, Any]] = None
    filing_date: Optional[str] = None
    property_address: Optional[str] = Field(None, max_length=500)
    catastro: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = None
    assigned_reviewer_id: Optional[str] = None


class DocumentTypeOverride(BaseModel):
    doc_type: str


# =============================================================================
# Shaping - what leaves the API
# =============================================================================

_CASE_FIELDS = (
    "id,case_number,permit_type,applicant_name,property_address,catastro,"
    "status,assigned_reviewer_id,ruleset_version_id,profile,filing_date,"
    "created_at,updated_at"
)

_DOCUMENT_FIELDS = (
    "id,case_id,filename,doc_type,doc_type_source,classification_band,"
    "classification_reason,classification_page,sha256,page_count,text_char_count,"
    "ocr_status,processing_status,processing_error,uploaded_at"
)


def _shape_document(row: Dict[str, Any]) -> Dict[str, Any]:
    """Add the display label; never expose the storage path or a numeric score."""
    return {
        **{k: v for k, v in row.items() if k != "storage_uri"},
        "doc_type_label": taxonomy.label_for(row.get("doc_type")),
    }


def _get_case_or_404(ctx: ReviewerContext, case_id: str) -> Dict[str, Any]:
    """
    Fetch a case in the caller's organization.

    A case belonging to another municipality is not visible to this query at all
    (Postgres filters it), so it produces the same 404 as one that does not
    exist - which is the correct amount to disclose.
    """
    case = ctx.db.select_one("cases", columns=_CASE_FIELDS, filters={"id": f"eq.{case_id}"})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expediente no encontrado.",
        )
    return case


# =============================================================================
# Identity and reference data
# =============================================================================

@router.get("/me")
def whoami(ctx: ReviewerContext = Depends(get_reviewer_context)):
    """
    The caller's reviewer identity. The frontend uses this to decide whether to
    show the console at all.
    """
    return {
        "user_id": str(ctx.user_id),
        "email": ctx.email,
        "org_id": ctx.org_id,
        "org_name": ctx.org_name,
        "municipality": ctx.municipality,
        "role": ctx.role,
        "can_write": ctx.can_write,
        "active_ruleset_id": ctx.active_ruleset_id,
    }


@router.get("/taxonomy")
def document_taxonomy(ctx: ReviewerContext = Depends(get_reviewer_context)):
    """The document types this office classifies into, including `desconocido`."""
    return taxonomy.permiso_unico_types()


# =============================================================================
# Cases
# =============================================================================

@router.get("/cases")
def list_cases(
    status_filter: Optional[str] = None,
    limit: int = 100,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    filters = {"org_id": f"eq.{ctx.org_id}"}
    if status_filter:
        filters["status"] = f"eq.{status_filter}"

    return ctx.db.select(
        "cases",
        columns=_CASE_FIELDS,
        filters=filters,
        order="created_at.desc",
        limit=min(limit, 200),
    )


@router.get("/cases/next-number")
def suggest_case_number(ctx: ReviewerContext = Depends(get_reviewer_context)):
    return {"case_number": intake.next_case_number(ctx)}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    data: CaseCreate,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    Open a case.

    The ruleset in force right now is stamped onto the case here and can never
    change afterwards (enforced by a database trigger), so a determination stays
    reproducible even after the regulations are updated.
    """
    ctx.require_write()

    if not ctx.active_ruleset_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Su oficina no tiene un reglamento activo configurado. "
                "No se puede abrir un expediente sin registrar la version de reglas aplicable."
            ),
        )

    case_number = (data.case_number or "").strip() or intake.next_case_number(ctx)

    payload = {
        "org_id": ctx.org_id,
        "case_number": case_number,
        "permit_type": data.permit_type,
        "applicant_name": data.applicant_name,
        "property_address": data.property_address,
        "catastro": data.catastro,
        "status": "recibido",
        "assigned_reviewer_id": str(ctx.user_id),
        "ruleset_version_id": ctx.active_ruleset_id,
    }

    try:
        rows = ctx.db.insert("cases", payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Case insert failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo crear el expediente.",
        )

    if not rows:
        # PostgREST returns 409 on the unique index, which surfaces as a 502
        # above; an empty body here means the row was rejected silently.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un expediente con el numero {case_number}.",
        )

    case = rows[0]
    audit.record(
        ctx,
        audit.CASE_CREATED,
        case_id=case["id"],
        object_ref=case["id"],
        payload={"case_number": case_number, "ruleset_version_id": ctx.active_ruleset_id},
    )
    return case


@router.get("/cases/{case_id}")
def get_case(case_id: str, ctx: ReviewerContext = Depends(get_reviewer_context)):
    case = _get_case_or_404(ctx, case_id)

    documents = ctx.db.select(
        "case_documents",
        columns=_DOCUMENT_FIELDS,
        filters={"case_id": f"eq.{case_id}"},
        order="uploaded_at.asc",
    )

    return {"case": case, "documents": [_shape_document(d) for d in documents]}


@router.patch("/cases/{case_id}")
def update_case(
    case_id: str,
    data: CaseUpdate,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    ctx.require_write()
    _get_case_or_404(ctx, case_id)

    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se recibieron cambios.",
        )

    rows = ctx.db.update("cases", filters={"id": f"eq.{case_id}"}, values=values)

    audit.record(
        ctx,
        audit.CASE_UPDATED,
        case_id=case_id,
        object_ref=case_id,
        payload={"changed": sorted(values.keys())},
    )
    return rows[0] if rows else {}


@router.get("/cases/{case_id}/audit")
def case_audit_trail(
    case_id: str,
    limit: int = 200,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    _get_case_or_404(ctx, case_id)
    return ctx.db.select(
        "audit_events",
        columns="id,event_type,object_ref,payload,actor_user_id,created_at",
        filters={"case_id": f"eq.{case_id}"},
        order="created_at.desc",
        limit=min(limit, 500),
    )


# =============================================================================
# Documents
# =============================================================================

@router.post("/cases/{case_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    case_id: str,
    files: List[UploadFile] = File(...),
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    Upload one or more PDFs to a case.

    Each file is processed independently: a rejected or unclassifiable file is
    reported in `rejected` while the rest are stored. A reviewer dropping five
    documents should not lose four of them because one was a photograph.
    """
    ctx.require_write()
    _get_case_or_404(ctx, case_id)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se recibieron archivos.",
        )
    if len(files) > intake.MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximo {intake.MAX_FILES_PER_REQUEST} archivos por carga.",
        )

    stored: List[Dict[str, Any]] = []
    rejected: List[Dict[str, str]] = []

    for upload in files:
        filename = upload.filename or "documento.pdf"
        try:
            content = await upload.read()
            stored.append(_shape_document(intake.ingest_document(ctx, case_id, filename, content)))
        except HTTPException as exc:
            rejected.append({"filename": filename, "reason": str(exc.detail)})
        except Exception as exc:
            logger.exception("Unexpected failure ingesting %s", filename)
            rejected.append(
                {"filename": filename, "reason": f"Error inesperado al procesar el archivo: {exc}"}
            )
        finally:
            await upload.close()

    if not stored and rejected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(f"{r['filename']}: {r['reason']}" for r in rejected),
        )

    return {"documents": stored, "rejected": rejected}


@router.get("/documents/{document_id}/url")
def document_url(document_id: str, ctx: ReviewerContext = Depends(get_reviewer_context)):
    """
    A short-lived link to read one document.

    Links are minted per request and expire in five minutes; the console never
    holds a durable URL to a case document.
    """
    document = ctx.db.select_one(
        "case_documents",
        columns="id,case_id,storage_uri,filename",
        filters={"id": f"eq.{document_id}"},
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        )

    url = intake.signed_document_url(ctx, document)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo generar el enlace del documento.",
        )

    audit.record(
        ctx,
        audit.DOCUMENT_VIEWED,
        case_id=document["case_id"],
        object_ref=document_id,
        payload={"filename": document.get("filename")},
    )

    return {"url": url, "expires_in": 300}


@router.patch("/documents/{document_id}")
def override_document_type(
    document_id: str,
    data: DocumentTypeOverride,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    A reviewer correcting the document type.

    A human decision is recorded as such: the band becomes `alta` because the
    evidence for the type is now a person who looked at it, and the audit trail
    keeps what the model had said.
    """
    ctx.require_write()

    if data.doc_type not in taxonomy.valid_codes():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de documento no valido: {data.doc_type}",
        )

    document = ctx.db.select_one(
        "case_documents",
        columns="id,case_id,doc_type,classification_band,classification_reason",
        filters={"id": f"eq.{document_id}"},
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        )

    rows = ctx.db.update(
        "case_documents",
        filters={"id": f"eq.{document_id}"},
        values={
            "doc_type": data.doc_type,
            "doc_type_source": "revisor",
            "classification_band": "alta",
            "classification_reason": "confirmado_por_revisor",
            "processing_status": "listo",
            "processing_error": None,
        },
    )

    audit.record(
        ctx,
        audit.DOCUMENT_TYPE_OVERRIDDEN,
        case_id=document["case_id"],
        object_ref=document_id,
        payload={
            "from": document.get("doc_type"),
            "to": data.doc_type,
            "model_band": document.get("classification_band"),
            "model_reason": document.get("classification_reason"),
        },
    )

    return _shape_document(rows[0]) if rows else {}


# =============================================================================
# Extraction and evaluation
# =============================================================================

@router.post("/cases/{case_id}/extract")
def extract_case_facts(
    case_id: str,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    Read the facts out of every classified document on the case.

    Each field is read twice - once from the text layer, once from the page
    images - and the band records whether the two agreed. Facts are appended,
    so re-running after a document is replaced supersedes without erasing.
    """
    ctx.require_write()
    _get_case_or_404(ctx, case_id)
    return evaluation.run_extraction(ctx, case_id)


@router.post("/cases/{case_id}/gis")
def run_gis_lookups(
    case_id: str,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    Geocode the property, read the parcel and the calificacion, and record a
    zoning-compatibility determination.

    Runs after extraction, because the proposed use is read off the applicant's
    own patente rather than inferred. Every outcome is recorded with its raw
    response; an outage, an ambiguous parcel or an unmapped activity all become
    a quality flag that makes the zoning rule escalate.
    """
    ctx.require_write()
    case = _get_case_or_404(ctx, case_id)
    return gis.run_lookups(ctx, case_id, case)


@router.post("/cases/{case_id}/evaluate")
def evaluate_case_rules(
    case_id: str,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    Run the rules against the extracted facts.

    Evaluated under the ruleset the case was stamped with when it was opened,
    not the office's current one.
    """
    ctx.require_write()
    case = _get_case_or_404(ctx, case_id)

    result = evaluation.run_evaluation(ctx, case_id, case)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["error"])
    return result


@router.get("/cases/{case_id}/checks")
def case_checks(
    case_id: str,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """
    The latest result of each rule on this case, newest evaluation first.

    Reads the whole append-only history and keeps the most recent row per rule,
    rather than relying on the database view, so the same shape comes back
    whether or not `compliance_checks_current` has been created.
    """
    _get_case_or_404(ctx, case_id)

    # Embed the rule so the screen can name the check instead of showing a uuid.
    # rule_id is a foreign key, so PostgREST resolves `rules(...)` for us.
    rows = ctx.db.select(
        "compliance_checks",
        columns=(
            "id,rule_id,family,status,band,evidence_ids,citations,explanation,"
            "reason_code,evaluated_at,rules(code,title,severity,citation,authority)"
        ),
        filters={"case_id": f"eq.{case_id}"},
        order="evaluated_at.desc",
    )

    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        latest.setdefault(row["rule_id"], row)

    checks = []
    for row in latest.values():
        rule = row.pop("rules", None) or {}
        checks.append(
            {
                **row,
                "rule_code": rule.get("code"),
                "rule_title": rule.get("title"),
                "severity": rule.get("severity"),
                "rule_citation": rule.get("citation"),
                "authority": rule.get("authority"),
            }
        )

    # Findings first, then what needs a person, then what passed. A reviewer
    # opens this screen to see what is wrong, not to read a list of successes.
    order = {"hallazgo_identificado": 0, "requiere_criterio": 1, "sin_hallazgos": 2}
    checks.sort(key=lambda c: (order.get(c["status"], 3), c.get("rule_code") or ""))
    counts = {
        "sin_hallazgos": sum(1 for c in checks if c["status"] == "sin_hallazgos"),
        "hallazgo_identificado": sum(1 for c in checks if c["status"] == "hallazgo_identificado"),
        "requiere_criterio": sum(1 for c in checks if c["status"] == "requiere_criterio"),
        "total_evaluadas": len(checks),
    }
    return {"resumen": counts, "verificaciones": checks}


@router.get("/cases/{case_id}/facts")
def case_facts(
    case_id: str,
    ctx: ReviewerContext = Depends(get_reviewer_context),
):
    """Extracted facts, newest reading of each field."""
    _get_case_or_404(ctx, case_id)

    rows = ctx.db.select(
        "extracted_facts",
        columns=(
            "id,document_id,field_key,value_text,value_date,value_num,"
            "source_page,band,status,extracted_at"
        ),
        filters={"case_id": f"eq.{case_id}"},
        order="extracted_at.desc",
    )

    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        latest.setdefault(row["field_key"], row)

    return {"campos": list(latest.values())}
