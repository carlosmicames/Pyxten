"""
Folders CRUD endpoints
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth import get_current_user
from app.models import Folder, FolderItem, Validation, Project
from app.schemas import (
    FolderCreate,
    FolderResponse,
    FolderItemCreate,
    FolderItemResponse,
    UserInfo,
    MessageResponse,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=List[FolderResponse])
def list_folders(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all folders for the current user"""
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == user.user_id)
        .order_by(Folder.created_at.desc())
        .all()
    )

    # Add item count
    results = []
    for folder in folders:
        item_count = (
            db.query(FolderItem)
            .filter(FolderItem.folder_id == folder.id)
            .count()
        )
        results.append(
            FolderResponse(
                id=folder.id,
                user_id=folder.user_id,
                name=folder.name,
                created_at=folder.created_at,
                item_count=item_count,
            )
        )

    return results


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new folder"""
    try:
        folder = Folder(
            user_id=user.user_id,
            name=folder_data.name,
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)

        return FolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            created_at=folder.created_at,
            item_count=0,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una carpeta con ese nombre",
        )


@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific folder"""
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == user.user_id)
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada",
        )

    item_count = (
        db.query(FolderItem)
        .filter(FolderItem.folder_id == folder.id)
        .count()
    )

    return FolderResponse(
        id=folder.id,
        user_id=folder.user_id,
        name=folder.name,
        created_at=folder.created_at,
        item_count=item_count,
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a folder"""
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == user.user_id)
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada",
        )

    db.delete(folder)
    db.commit()
    return None


@router.get("/{folder_id}/items", response_model=List[FolderItemResponse])
def list_folder_items(
    folder_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List items in a folder

    Joins folder_items -> validations -> projects to return:
    - Project Name
    - Address
    - Validation Date (created_at)
    - Viable
    """
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == user.user_id)
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada",
        )

    items = (
        db.query(FolderItem)
        .filter(FolderItem.folder_id == folder_id)
        .order_by(FolderItem.created_at.desc())
        .all()
    )

    results = []
    for item in items:
        # Get validation
        validation = (
            db.query(Validation)
            .filter(Validation.id == item.validation_id)
            .first()
        )

        if not validation:
            continue

        # Get project
        project = None
        project_name = "N/A"
        project_address = validation.property_address or "N/A"

        if validation.project_id:
            project = db.query(Project).filter(Project.id == validation.project_id).first()
            if project:
                project_name = project.name
                project_address = project.address or project_address

        results.append(
            FolderItemResponse(
                id=item.id,
                folder_id=item.folder_id,
                validation_id=item.validation_id,
                created_at=item.created_at,
                project_name=project_name,
                project_address=project_address,
                validation_date=validation.created_at,
                viable=validation.viable,
            )
        )

    return results


@router.post("/{folder_id}/items", response_model=FolderItemResponse, status_code=status.HTTP_201_CREATED)
def add_folder_item(
    folder_id: UUID,
    item_data: FolderItemCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a validation to a folder

    Returns 409 error with "Ya existe en la carpeta" if validation is already in folder.
    """
    # Verify folder exists and belongs to user
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == user.user_id)
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada",
        )

    # Verify validation exists and belongs to user
    validation = (
        db.query(Validation)
        .filter(
            Validation.id == item_data.validation_id,
            Validation.user_id == user.user_id,
        )
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validacion no encontrada",
        )

    # Check if already exists
    existing = (
        db.query(FolderItem)
        .filter(
            FolderItem.folder_id == folder_id,
            FolderItem.validation_id == item_data.validation_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe en la carpeta",
        )

    # Create item
    try:
        item = FolderItem(
            user_id=user.user_id,
            folder_id=folder_id,
            validation_id=item_data.validation_id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Get project info for response
        project = None
        project_name = "N/A"
        project_address = validation.property_address or "N/A"

        if validation.project_id:
            project = db.query(Project).filter(Project.id == validation.project_id).first()
            if project:
                project_name = project.name
                project_address = project.address or project_address

        return FolderItemResponse(
            id=item.id,
            folder_id=item.folder_id,
            validation_id=item.validation_id,
            created_at=item.created_at,
            project_name=project_name,
            project_address=project_address,
            validation_date=validation.created_at,
            viable=validation.viable,
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe en la carpeta",
        )


@router.delete("/{folder_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder_item(
    folder_id: UUID,
    item_id: UUID,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an item from a folder"""
    item = (
        db.query(FolderItem)
        .filter(
            FolderItem.id == item_id,
            FolderItem.folder_id == folder_id,
            FolderItem.user_id == user.user_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado",
        )

    db.delete(item)
    db.commit()
    return None
