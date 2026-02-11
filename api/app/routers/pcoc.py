"""
PCOC Validations endpoints (Permiso de Construccion)
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import PCOCValidation, Project
from app.schemas import (
    PCOCValidationCreate,
    PCOCValidationUpdate,
    PCOCValidationResponse,
    PCOCValidationListResponse,
    UserInfo,
)
from app.services.pcoc_service import PCOCService
from app.services.pcoc_pdf_generator import PCOCPDFGenerator

router = APIRouter(prefix="/pcoc", tags=["pcoc"])


@router.get("", response_model=List[PCOCValidationListResponse])
def list_pcoc_validations(
    limit: int = 50,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List PCOC validations for the current user"""
    validations = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.user_id == user.user_id)
        .order_by(PCOCValidation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return validations


@router.post("", response_model=PCOCValidationResponse, status_code=status.HTTP_201_CREATED)
def create_pcoc_validation(
    data: PCOCValidationCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new PCOC validation"""
    # If project_id provided, fetch project data
    project_name = data.project_name
    property_address = data.property_address
    municipality = data.municipality
    zoning_code = data.zoning_code

    if data.project_id:
        project = (
            db.query(Project)
            .filter(Project.id == data.project_id, Project.user_id == user.user_id)
            .first()
        )
        if project:
            project_name = project_name or project.name
            property_address = property_address or project.address
            municipality = municipality or project.municipality
            zoning_code = zoning_code or project.zoning_code

    validation = PCOCValidation(
        user_id=user.user_id,
        project_id=data.project_id,
        project_name=project_name,
        property_address=property_address,
        municipality=municipality,
        zoning_code=zoning_code,
        current_step=1,
        status="en_progreso",
    )

    db.add(validation)
    db.commit()
    db.refresh(validation)

    return validation


@router.get("/exempt-categories")
def get_exempt_categories():
    """Get the list of exempt work categories (Sec 3.2.4 RC)"""
    return PCOCService.get_exempt_categories()


@router.get("/categorical-exclusions")
def get_categorical_exclusions():
    """Get the list of categorical exclusions (OA 2025-10 DRNA)"""
    return PCOCService.get_categorical_exclusions()


@router.get("/district-parameters/{zoning_code}")
def get_district_parameters(
    zoning_code: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get the parameters for a specific zoning district for Filter 3 comparison"""
    params = PCOCService.get_district_parameters(zoning_code)
    if not params:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distrito {zoning_code} no encontrado",
        )
    return params


@router.get("/{pcoc_id}", response_model=PCOCValidationResponse)
def get_pcoc_validation(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific PCOC validation"""
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )
    return validation


@router.patch("/{pcoc_id}", response_model=PCOCValidationResponse)
def update_pcoc_validation(
    pcoc_id: UUID,
    data: PCOCValidationUpdate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a PCOC validation"""
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(validation, field, value)

    db.commit()
    db.refresh(validation)

    return validation


@router.post("/{pcoc_id}/analyze-filter1")
def analyze_filter1(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze Filter 1 data and determine if work is exempt.
    Updates the validation with the analysis result.
    """
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    if not validation.filter1_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe completar el Filtro 1 primero",
        )

    # Analyze using the service
    result = PCOCService.analyze_filter1(validation.filter1_data)

    # Update the validation with analysis result
    validation.filter1_data = {**validation.filter1_data, **result}
    db.commit()
    db.refresh(validation)

    return {"filter1_data": validation.filter1_data}


@router.post("/{pcoc_id}/analyze-filter2")
def analyze_filter2(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze Filter 2 data and determine required recommendations.
    """
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    if not validation.filter2_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe completar el Filtro 2 primero",
        )

    # Analyze using the service
    result = PCOCService.analyze_filter2(validation.filter2_data)

    # Update the validation with analysis result
    validation.filter2_data = {**validation.filter2_data, **result}
    db.commit()
    db.refresh(validation)

    return {"filter2_data": validation.filter2_data}


@router.post("/{pcoc_id}/analyze-filter3")
def analyze_filter3(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze Filter 3 data and determine if ministerial or discretionary.
    """
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    if not validation.filter3_data or not validation.zoning_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe completar el Filtro 3 y tener un codigo de zonificacion",
        )

    # Analyze using the service
    result = PCOCService.analyze_filter3(validation.filter3_data, validation.zoning_code)

    # Update the validation with analysis result
    validation.filter3_data = {**validation.filter3_data, **result}
    db.commit()
    db.refresh(validation)

    return {"filter3_data": validation.filter3_data}


@router.post("/{pcoc_id}/analyze-filter4")
def analyze_filter4(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze Filter 4 data for environmental compliance (categorical exclusions).
    """
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    proposed_use = ""
    if validation.filter1_data:
        proposed_use = validation.filter1_data.get("proposed_use", "")

    # Analyze using the service
    result = PCOCService.analyze_filter4(proposed_use)

    # Update the validation with analysis result
    validation.filter4_data = result
    db.commit()
    db.refresh(validation)

    return {"filter4_data": validation.filter4_data}


@router.post("/{pcoc_id}/generate-result")
def generate_result(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate the final PCOC validation result based on all filters.
    """
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    # Generate result using the service
    result = PCOCService.generate_final_result(validation)

    # Update the validation with final result
    validation.result = result
    validation.status = "completado"
    validation.current_step = 5
    db.commit()
    db.refresh(validation)

    return {"result": validation.result}


@router.get("/{pcoc_id}/report.pdf")
def get_pcoc_report_pdf(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and return PDF report for a PCOC validation"""
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    if not validation.result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe completar la validacion antes de generar el PDF",
        )

    # Generate PDF
    pdf_generator = PCOCPDFGenerator()
    pdf_bytes = pdf_generator.generate_report(validation)

    # Return PDF response
    filename = f"pcoc_validacion_{pcoc_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{pcoc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pcoc_validation(
    pcoc_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a PCOC validation"""
    validation = (
        db.query(PCOCValidation)
        .filter(PCOCValidation.id == pcoc_id, PCOCValidation.user_id == user.user_id)
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion PCOC no encontrada",
        )

    db.delete(validation)
    db.commit()
    return None
