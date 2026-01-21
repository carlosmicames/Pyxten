"""
Pydantic v2 schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


# ============================================================================
# Projects
# ============================================================================

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    address: Optional[str] = None
    municipality: Optional[str] = None
    catastro_number: Optional[str] = None
    calificacion: Optional[str] = None
    zoning_code: Optional[str] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    municipality: Optional[str] = None
    catastro_number: Optional[str] = None
    calificacion: Optional[str] = None
    zoning_code: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    address: Optional[str] = None
    municipality: Optional[str] = None
    catastro_number: Optional[str] = None
    calificacion: Optional[str] = None
    zoning_code: Optional[str] = None
    status: Optional[str] = None
    phase1_completed: bool = False
    phase1_result: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Validations
# ============================================================================

class ValidateFase1Request(BaseModel):
    project_description: str = Field(..., min_length=1)


class ValidationResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    validation_type: str
    result: Dict[str, Any]
    viable: bool
    project_description: Optional[str] = None
    property_address: Optional[str] = None
    created_at: datetime
    # Joined fields from project
    project_name: Optional[str] = None
    project_address: Optional[str] = None
    project_municipality: Optional[str] = None

    class Config:
        from_attributes = True


class ValidationListResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    validation_type: str
    viable: bool
    project_description: Optional[str] = None
    property_address: Optional[str] = None
    created_at: datetime
    # Joined fields from project
    project_name: Optional[str] = None
    project_address: Optional[str] = None
    project_municipality: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Folders
# ============================================================================

class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1)


class FolderResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    item_count: int = 0

    class Config:
        from_attributes = True


class FolderItemCreate(BaseModel):
    validation_id: UUID


class FolderItemResponse(BaseModel):
    id: UUID
    folder_id: UUID
    validation_id: UUID
    created_at: datetime
    # Joined fields
    project_name: Optional[str] = None
    project_address: Optional[str] = None
    validation_date: Optional[datetime] = None
    viable: bool = False

    class Config:
        from_attributes = True


# ============================================================================
# Auth
# ============================================================================

class UserInfo(BaseModel):
    user_id: UUID
    email: Optional[str] = None


# ============================================================================
# Generic
# ============================================================================

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
