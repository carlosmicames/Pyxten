"""
Projects CRUD endpoints
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import Project, Validation
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    UserInfo,
    ValidateFase1Request,
    ValidationResponse,
)
from app.services.validation_service import Phase1ValidationService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all projects for the current user"""
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.user_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project"""
    project = Project(
        user_id=user.user_id,
        name=project_data.name,
        address=project_data.address,
        municipality=project_data.municipality,
        catastro_number=project_data.catastro_number,
        calificacion=project_data.calificacion,
        zoning_code=project_data.zoning_code,
        notes=project_data.notes,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific project"""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a project"""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project"""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    db.delete(project)
    db.commit()
    return None


@router.post("/{project_id}/validate_fase1", response_model=ValidationResponse)
def validate_fase1(
    project_id: UUID,
    request: ValidateFase1Request,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run Phase 1 validation for a project

    This performs zoning compatibility validation based on:
    - Project address and municipality
    - Project description (natural language use description)
    """
    # Get project
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    if not project.address or not project.municipality:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proyecto debe tener direccion y municipio para validar",
        )

    if not request.district_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe seleccionar una calificacion/distrito de zonificacion",
        )

    # Run validation
    validation_service = Phase1ValidationService()
    result = validation_service.validate(
        address=project.address,
        municipality=project.municipality,
        project_description=request.project_description,
        district_code=request.district_code,
    )

    # Determine viability
    viable = result.get("final_result", {}).get("viable", False)

    # Store validation
    validation = Validation(
        user_id=user.user_id,
        project_id=project.id,
        validation_type="fase1",
        result=result,
        viable=viable,
        project_description=request.project_description,
        property_address=project.address,
    )
    db.add(validation)

    # Update project
    project.phase1_completed = True
    project.phase1_result = result

    # Update zoning_code from result if found
    final_result = result.get("final_result", {})
    if final_result.get("zoning_code"):
        project.zoning_code = final_result.get("zoning_code")
        project.calificacion = final_result.get("zoning_name")

    db.commit()
    db.refresh(validation)

    # Return response with joined project fields
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
        project_name=project.name,
        project_address=project.address,
        project_municipality=project.municipality,
    )
