"""
Validations endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import Validation, Project
from app.schemas import ValidationListResponse, ValidationResponse, UserInfo
from app.services.pdf_generator import PDFReportGenerator

router = APIRouter(prefix="/validations", tags=["validations"])


@router.get("", response_model=List[ValidationListResponse])
def list_validations(
    project_id: Optional[UUID] = None,
    limit: int = 50,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List validations for the current user

    Optionally filter by project_id.
    Joins with projects table to return project name/address/municipality.
    """
    query = db.query(Validation).filter(Validation.user_id == user.user_id)

    if project_id:
        query = query.filter(Validation.project_id == project_id)

    validations = query.order_by(Validation.created_at.desc()).limit(limit).all()

    # Build response with joined project fields
    results = []
    for validation in validations:
        project = None
        if validation.project_id:
            project = db.query(Project).filter(Project.id == validation.project_id).first()

        results.append(
            ValidationListResponse(
                id=validation.id,
                user_id=validation.user_id,
                project_id=validation.project_id,
                validation_type=validation.validation_type,
                viable=validation.viable,
                project_description=validation.project_description,
                property_address=validation.property_address,
                created_at=validation.created_at,
                project_name=project.name if project else None,
                project_address=project.address if project else validation.property_address,
                project_municipality=project.municipality if project else None,
            )
        )

    return results


@router.get("/{validation_id}", response_model=ValidationResponse)
def get_validation(
    validation_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific validation with full result"""
    validation = (
        db.query(Validation)
        .filter(Validation.id == validation_id, Validation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion no encontrada",
        )

    # Get project for joined fields
    project = None
    if validation.project_id:
        project = db.query(Project).filter(Project.id == validation.project_id).first()

    return ValidationResponse(
        id=validation.id,
        user_id=validation.user_id,
        project_id=validation.project_id,
        validation_type=validation.validation_type,
        result=validation.result,
        viable=validation.viable,
        project_description=validation.project_description,
        property_address=validation.property_address,
        created_at=validation.created_at,
        project_name=project.name if project else None,
        project_address=project.address if project else validation.property_address,
        project_municipality=project.municipality if project else None,
    )


@router.get("/{validation_id}/report.pdf")
def get_validation_report_pdf(
    validation_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and return PDF report for a validation

    The PDF follows strict wording requirements:
    - If viable: "El proyecto cumple con los requisitos de zonificacion en esa area."
    - If NOT viable: "El uso propuesto no es compatible con la zonificacion."
    - Does NOT include "Proximos Pasos recomendados" section
    """
    validation = (
        db.query(Validation)
        .filter(Validation.id == validation_id, Validation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion no encontrada",
        )

    # Get project for joined fields
    project = None
    project_name = "N/A"
    project_address = validation.property_address or "N/A"
    project_municipality = "N/A"

    if validation.project_id:
        project = db.query(Project).filter(Project.id == validation.project_id).first()
        if project:
            project_name = project.name
            project_address = project.address or project_address
            project_municipality = project.municipality or "N/A"

    # Generate PDF
    pdf_generator = PDFReportGenerator()
    pdf_bytes = pdf_generator.generate_report(
        validation_result=validation.result,
        project_name=project_name,
        project_address=project_address,
        project_municipality=project_municipality,
    )

    # Return PDF response
    filename = f"validacion_{validation_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
