"""
SQLAlchemy models matching Supabase schema
"""
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(Text, nullable=False)
    address = Column(Text)
    municipality = Column(Text)
    catastro_number = Column(Text)
    calificacion = Column(Text)
    zoning_code = Column(Text)
    status = Column(Text, default="En Progreso")
    phase1_completed = Column(Boolean, default=False)
    phase1_result = Column(JSONB)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    validations = relationship("Validation", back_populates="project")


class Validation(Base):
    __tablename__ = "validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    validation_type = Column(Text, nullable=False, default="fase1")
    result = Column(JSONB, nullable=False)
    viable = Column(Boolean, default=False)
    project_description = Column(Text)
    property_address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="validations")


class UsageTracking(Base):
    __tablename__ = "usage_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    period = Column(Text, nullable=False)
    validations_used = Column(Integer, default=0)
    tier = Column(Text, default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("FolderItem", back_populates="folder", cascade="all, delete-orphan")


class FolderItem(Base):
    __tablename__ = "folder_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=False)
    validation_id = Column(UUID(as_uuid=True), ForeignKey("validations.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    folder = relationship("Folder", back_populates="items")
    validation = relationship("Validation")


class PCOCValidation(Base):
    """
    PCOC (Permiso de Construcción) Validation
    Stores the multi-step construction permit validation checklist
    """
    __tablename__ = "pcoc_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))

    # Basic project info (can be from linked project or manual entry)
    project_name = Column(Text)
    property_address = Column(Text)
    municipality = Column(Text)
    zoning_code = Column(Text)

    # Current step in the workflow
    current_step = Column(Integer, default=1)  # 1-5 (filters 1-4 + result)
    status = Column(Text, default="en_progreso")  # en_progreso, completado, requiere_accion

    # Filter 1: Requiere Permiso de Construcción
    filter1_data = Column(JSONB)  # proposed_use, exempt_selections, ai_interpretation, is_exempt, etc.

    # Filter 2: Ubicación (Zonas Sobrepuestas)
    filter2_data = Column(JSONB)  # zona_historica, zona_turistica, zona_inundacion, auto_detected, user_overrides

    # Filter 3: Clasificación del Trámite (Ministerial vs Discrecional)
    filter3_data = Column(JSONB)  # project_params, district_requirements, comparison_results, is_ministerial

    # Filter 4: Cumplimiento Ambiental
    filter4_data = Column(JSONB)  # categorical_exclusion_check, requires_ea_dia, exclusion_category

    # Final result
    result = Column(JSONB)  # summary, action_items, recommendations, permit_type

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project")
