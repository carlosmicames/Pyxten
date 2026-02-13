"""
Document Validation endpoints
Handles document checklist validation and Memorial Explicativo generation
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_active_subscription
from app.models import DocumentValidation, PCOCValidation
from app.schemas import (
    DocumentValidationCreate,
    DocumentValidationUpdate,
    DocumentValidationResponse,
    DocumentValidationListResponse,
    UserInfo,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/requirements/pcoc")
def get_pcoc_requirements():
    """Get the list of required documents for PCOC validation"""
    return DocumentService.get_pcoc_requirements()


@router.get("/requirements/permiso-unico")
def get_permiso_unico_requirements():
    """Get the list of required documents for Permiso Unico"""
    return DocumentService.get_permiso_unico_requirements()


@router.get("", response_model=List[DocumentValidationListResponse])
def list_document_validations(
    validation_type: str = None,
    limit: int = 50,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List document validations for the current user"""
    query = db.query(DocumentValidation).filter(DocumentValidation.user_id == user.user_id)

    if validation_type:
        query = query.filter(DocumentValidation.validation_type == validation_type)

    validations = (
        query
        .order_by(DocumentValidation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return validations


@router.post("", response_model=DocumentValidationResponse, status_code=status.HTTP_201_CREATED)
def create_document_validation(
    data: DocumentValidationCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new document validation"""
    require_active_subscription(user, db)

    # If pcoc_validation_id provided, fetch PCOC data
    project_name = data.project_name
    property_address = data.property_address
    municipality = data.municipality

    if data.pcoc_validation_id:
        pcoc = (
            db.query(PCOCValidation)
            .filter(PCOCValidation.id == data.pcoc_validation_id, PCOCValidation.user_id == user.user_id)
            .first()
        )
        if pcoc:
            project_name = project_name or pcoc.project_name
            property_address = property_address or pcoc.property_address
            municipality = municipality or pcoc.municipality

    # Initialize documents checklist
    documents = DocumentService.initialize_documents_checklist(data.validation_type)

    validation = DocumentValidation(
        user_id=user.user_id,
        pcoc_validation_id=data.pcoc_validation_id,
        validation_type=data.validation_type,
        project_name=project_name,
        property_address=property_address,
        municipality=municipality,
        status="en_progreso",
        documents=documents,
        memorial_explicativo={},
    )

    db.add(validation)
    db.commit()
    db.refresh(validation)

    return validation


@router.get("/{doc_id}", response_model=DocumentValidationResponse)
def get_document_validation(
    doc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific document validation"""
    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )
    return validation


@router.patch("/{doc_id}", response_model=DocumentValidationResponse)
def update_document_validation(
    doc_id: UUID,
    data: DocumentValidationUpdate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a document validation"""
    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )

    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(validation, field, value)

    db.commit()
    db.refresh(validation)

    return validation


@router.post("/{doc_id}/update-document/{doc_code}")
def update_document_status(
    doc_id: UUID,
    doc_code: str,
    uploaded: bool = False,
    file_url: str = None,
    file_name: str = None,
    verified: bool = False,
    notes: str = None,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the status of a specific document in the checklist"""
    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )

    documents = validation.documents or {}
    if doc_code not in documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Codigo de documento '{doc_code}' no valido",
        )

    # Update the document status
    documents[doc_code]["uploaded"] = uploaded
    if file_url is not None:
        documents[doc_code]["file_url"] = file_url
    if file_name is not None:
        documents[doc_code]["file_name"] = file_name
    documents[doc_code]["verified"] = verified
    if notes is not None:
        documents[doc_code]["notes"] = notes

    validation.documents = documents
    db.commit()
    db.refresh(validation)

    return {"documents": validation.documents, "updated_code": doc_code}


@router.post("/{doc_id}/validate")
def validate_documents(
    doc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate the completeness of all documents"""
    require_active_subscription(user, db)

    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )

    # Validate documents completeness
    result = DocumentService.validate_documents_completeness(
        validation.documents or {},
        validation.validation_type
    )

    # Update status based on completeness
    if result["is_complete"]:
        validation.status = "completo"
    else:
        validation.status = "requiere_documentos"

    db.commit()
    db.refresh(validation)

    return {
        "validation_result": result,
        "status": validation.status,
    }


@router.post("/{doc_id}/generate-memorial")
def generate_memorial_explicativo(
    doc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate Memorial Explicativo content for the document validation"""
    require_active_subscription(user, db)

    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )

    # Get PCOC data if linked
    pcoc_data = None
    if validation.pcoc_validation_id:
        pcoc = (
            db.query(PCOCValidation)
            .filter(PCOCValidation.id == validation.pcoc_validation_id)
            .first()
        )
        if pcoc:
            pcoc_data = {
                "zoning_code": pcoc.zoning_code,
                "filter1_data": pcoc.filter1_data,
                "filter2_data": pcoc.filter2_data,
                "filter3_data": pcoc.filter3_data,
                "filter4_data": pcoc.filter4_data,
                "result": pcoc.result,
            }

    # Generate Memorial Explicativo
    memorial = DocumentService.generate_memorial_explicativo(
        project_name=validation.project_name or "",
        property_address=validation.property_address or "",
        municipality=validation.municipality or "",
        pcoc_data=pcoc_data,
    )

    # Update the validation
    validation.memorial_explicativo = memorial
    db.commit()
    db.refresh(validation)

    return {"memorial_explicativo": validation.memorial_explicativo}


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_validation(
    doc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document validation"""
    validation = (
        db.query(DocumentValidation)
        .filter(DocumentValidation.id == doc_id, DocumentValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion de documentos no encontrada",
        )

    db.delete(validation)
    db.commit()
    return None
