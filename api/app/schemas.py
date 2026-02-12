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
# Address Validation
# ============================================================================

class AddressValidationRequest(BaseModel):
    address: str = Field(..., min_length=1)
    municipality: str = Field(..., min_length=1)


class AddressValidationResponse(BaseModel):
    valid: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    catastro_number: Optional[str] = None
    municipality: Optional[str] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    gis_map_url: str = "https://gis.jp.pr.gov/mipr/"
    disclaimer: str = "Debe verificar esta informacion en el mapa oficial para confirmar su exactitud antes de continuar."
    error: Optional[str] = None


# ============================================================================
# Validations
# ============================================================================

class ValidateFase1Request(BaseModel):
    project_description: str = Field(..., min_length=1)
    district_code: str = Field(..., min_length=1, description="User-selected zoning district code")


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
# Usage Statistics
# ============================================================================

class UsageStatsResponse(BaseModel):
    period: str
    total_validations: int
    viable_validations: int
    non_viable_validations: int


# ============================================================================
# Auth
# ============================================================================

class UserInfo(BaseModel):
    user_id: UUID
    email: Optional[str] = None


# ============================================================================
# PCOC Validations (Construction Permit)
# ============================================================================

class PCOCFilter1Data(BaseModel):
    """Filter 1: Requiere Permiso de Construccion?"""
    proposed_use: Optional[str] = None
    exempt_selections: Optional[List[str]] = None  # List of selected exempt category codes
    ai_interpretation: Optional[str] = None
    is_exempt: Optional[bool] = None
    exempt_reason: Optional[str] = None


class PCOCFilter2Data(BaseModel):
    """Filter 2: Ubicacion (Zonas Sobrepuestas)"""
    zona_historica: Optional[bool] = None
    zona_historica_auto: Optional[bool] = None  # Auto-detected value
    zona_turistica: Optional[bool] = None
    zona_turistica_auto: Optional[bool] = None
    zona_inundacion: Optional[bool] = None
    zona_inundacion_auto: Optional[bool] = None
    required_recommendations: Optional[List[str]] = None  # ICP, Turismo, DRNA, etc.


class PCOCFilter3Data(BaseModel):
    """Filter 3: Clasificacion del Tramite (Ministerial vs Discrecional)"""
    project_params: Optional[Dict[str, Any]] = None  # altura, area_ocupacion, etc.
    district_requirements: Optional[Dict[str, Any]] = None  # From rules_data
    comparison_results: Optional[List[Dict[str, Any]]] = None  # Per-parameter comparison
    is_ministerial: Optional[bool] = None
    non_compliant_params: Optional[List[str]] = None


class PCOCFilter4Data(BaseModel):
    """Filter 4: Cumplimiento Ambiental"""
    is_categorical_exclusion: Optional[bool] = None
    exclusion_category: Optional[str] = None
    exclusion_reason: Optional[str] = None
    requires_ea_dia: Optional[bool] = None


class PCOCResultData(BaseModel):
    """Final PCOC validation result"""
    summary: Optional[str] = None
    permit_type: Optional[str] = None  # obra_exenta, ministerial, discrecional
    action_items: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None
    viable: Optional[bool] = None


class PCOCValidationCreate(BaseModel):
    """Create a new PCOC validation"""
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    zoning_code: Optional[str] = None


class PCOCValidationUpdate(BaseModel):
    """Update a PCOC validation"""
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    zoning_code: Optional[str] = None
    current_step: Optional[int] = None
    status: Optional[str] = None
    filter1_data: Optional[Dict[str, Any]] = None
    filter2_data: Optional[Dict[str, Any]] = None
    filter3_data: Optional[Dict[str, Any]] = None
    filter4_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class PCOCValidationResponse(BaseModel):
    """PCOC validation response"""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    zoning_code: Optional[str] = None
    current_step: int = 1
    status: str = "en_progreso"
    filter1_data: Optional[Dict[str, Any]] = None
    filter2_data: Optional[Dict[str, Any]] = None
    filter3_data: Optional[Dict[str, Any]] = None
    filter4_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PCOCValidationListResponse(BaseModel):
    """PCOC validation list item"""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    current_step: int = 1
    status: str = "en_progreso"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Document Validations
# ============================================================================

class DocumentStatus(BaseModel):
    """Status of a single document in the checklist"""
    required: bool = True
    optional: bool = False
    uploaded: bool = False
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    verified: bool = False
    notes: Optional[str] = None


class MemorialExplicativoContent(BaseModel):
    """Content structure for Memorial Explicativo"""
    generated: bool = False
    project_description: Optional[str] = None
    location_description: Optional[str] = None
    zoning_info: Optional[str] = None
    construction_details: Optional[str] = None
    environmental_compliance: Optional[str] = None
    permit_type_justification: Optional[str] = None
    additional_notes: Optional[str] = None
    pdf_url: Optional[str] = None


class DocumentValidationCreate(BaseModel):
    """Create a new document validation"""
    pcoc_validation_id: Optional[UUID] = None
    validation_type: str = "pcoc"
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None


class DocumentValidationUpdate(BaseModel):
    """Update a document validation"""
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    status: Optional[str] = None
    documents: Optional[Dict[str, Any]] = None
    memorial_explicativo: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class DocumentValidationResponse(BaseModel):
    """Document validation response"""
    id: UUID
    user_id: UUID
    pcoc_validation_id: Optional[UUID] = None
    validation_type: str = "pcoc"
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    status: str = "en_progreso"
    documents: Optional[Dict[str, Any]] = None
    memorial_explicativo: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentValidationListResponse(BaseModel):
    """Document validation list item"""
    id: UUID
    user_id: UUID
    pcoc_validation_id: Optional[UUID] = None
    validation_type: str = "pcoc"
    project_name: Optional[str] = None
    property_address: Optional[str] = None
    municipality: Optional[str] = None
    status: str = "en_progreso"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentRequirement(BaseModel):
    """A single document requirement definition"""
    code: str
    name: str
    description: str
    required: bool = True
    conditional: Optional[str] = None  # Condition for when document is required


# ============================================================================
# Generic
# ============================================================================

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
