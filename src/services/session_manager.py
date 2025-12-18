# Session Manager - CORREGIDO para evitar recursión
import streamlit as st
from datetime import datetime
from typing import Dict, Optional, List
import json

class SessionManager:
    """
    Gestiona el estado de sesión de Streamlit
    Guarda proyectos, documentos y validaciones en memoria
    """
    
    @staticmethod
    def initialize():
        """Inicializa todas las variables de sesión necesarias"""
        
        # Proyectos activos
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        
        # Proyecto actual
        if 'current_project_id' not in st.session_state:
            st.session_state.current_project_id = None
        
        # Contador de validaciones (para free tier)
        if 'validation_count' not in st.session_state:
            st.session_state.validation_count = 0
        
        # Límite de validaciones gratis
        if 'validation_limit' not in st.session_state:
            st.session_state.validation_limit = 5
        
        # Navegación - IMPORTANTE: default es 'dashboard'
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'homepage'
        
        # Historial de validaciones (últimas 10)
        if 'validation_history' not in st.session_state:
            st.session_state.validation_history = []
        
        # UI State
        if 'show_projects_menu' not in st.session_state:
            st.session_state.show_projects_menu = False
        
        if 'show_help' not in st.session_state:
            st.session_state.show_help = False
    
    @staticmethod
    def create_project(name: str, address: str, municipality: str) -> str:
        """
        Crea un nuevo proyecto
        
        Args:
            name: Nombre del proyecto
            address: Dirección de la propiedad
            municipality: Municipio
        
        Returns:
            project_id: ID único del proyecto
        """
        # Generar ID único basado en timestamp
        project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Crear estructura del proyecto
        st.session_state.projects[project_id] = {
            'id': project_id,
            'name': name,
            'address': address,
            'municipality': municipality,
            'created_date': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'status': 'En Progreso',
            'phase1_completed': False,
            'phase1_result': None,
            'documents': {},
            'reports': [],
            'notes': ''
        }
        
        # Establecer como proyecto actual
        st.session_state.current_project_id = project_id
        
        return project_id
    
    @staticmethod
    def get_project(project_id: str) -> Optional[Dict]:
        """Obtiene un proyecto por ID"""
        return st.session_state.projects.get(project_id)
    
    @staticmethod
    def get_current_project() -> Optional[Dict]:
        """Obtiene el proyecto actual"""
        if st.session_state.current_project_id:
            return SessionManager.get_project(st.session_state.current_project_id)
        return None
    
    @staticmethod
    def update_project(project_id: str, updates: Dict):
        """Actualiza datos de un proyecto"""
        if project_id in st.session_state.projects:
            st.session_state.projects[project_id].update(updates)
            st.session_state.projects[project_id]['last_modified'] = datetime.now().isoformat()
    
    @staticmethod
    def delete_project(project_id: str):
        """Elimina un proyecto"""
        if project_id in st.session_state.projects:
            del st.session_state.projects[project_id]
            
            # Si era el proyecto actual, limpiarlo
            if st.session_state.current_project_id == project_id:
                st.session_state.current_project_id = None
    
    @staticmethod
    def set_current_project(project_id: Optional[str]):
        """Establece el proyecto actual"""
        st.session_state.current_project_id = project_id
    
    @staticmethod
    def get_all_projects() -> Dict:
        """Obtiene todos los proyectos"""
        return st.session_state.projects
    
    @staticmethod
    def get_active_projects() -> List[Dict]:
        """Obtiene proyectos activos (no completados)"""
        return [
            project for project in st.session_state.projects.values()
            if project['status'] != 'Completado'
        ]
    
    @staticmethod
    def add_validation_to_history(validation_result: Dict):
        """Agrega una validación al historial"""
        # Agregar timestamp
        validation_result['timestamp'] = datetime.now().isoformat()
        
        # Agregar al historial (mantener últimos 10)
        st.session_state.validation_history.insert(0, validation_result)
        st.session_state.validation_history = st.session_state.validation_history[:10]
        
        # Incrementar contador
        st.session_state.validation_count += 1
    
    @staticmethod
    def get_validation_history() -> List[Dict]:
        """Obtiene el historial de validaciones"""
        return st.session_state.validation_history
    
    @staticmethod
    def can_validate() -> bool:
        """Verifica si puede hacer más validaciones gratis"""
        return st.session_state.validation_count < st.session_state.validation_limit
    
    @staticmethod
    def get_remaining_validations() -> int:
        """Obtiene validaciones restantes"""
        remaining = st.session_state.validation_limit - st.session_state.validation_count
        return max(0, remaining)
    
    @staticmethod
    def add_document_to_project(project_id: str, doc_type: str, file_data: bytes, filename: str):
        """Agrega un documento a un proyecto"""
        if project_id in st.session_state.projects:
            st.session_state.projects[project_id]['documents'][doc_type] = {
                'filename': filename,
                'data': file_data,
                'uploaded_date': datetime.now().isoformat(),
                'validated': False,
                'validation_result': None
            }
            st.session_state.projects[project_id]['last_modified'] = datetime.now().isoformat()
    
    @staticmethod
    def add_report_to_project(project_id: str, report_type: str, report_data: bytes):
        """Agrega un reporte generado a un proyecto"""
        if project_id in st.session_state.projects:
            st.session_state.projects[project_id]['reports'].append({
                'type': report_type,
                'generated_date': datetime.now().isoformat(),
                'data': report_data
            })
    
    @staticmethod
    def export_project(project_id: str) -> Dict:
        """Exporta un proyecto como JSON (para download)"""
        project = SessionManager.get_project(project_id)
        if project:
            # Crear copia sin datos binarios (muy pesados)
            export_data = project.copy()
            
            # Remover datos binarios, mantener solo metadatos
            if 'documents' in export_data:
                for doc_type in export_data['documents']:
                    if 'data' in export_data['documents'][doc_type]:
                        del export_data['documents'][doc_type]['data']
            
            if 'reports' in export_data:
                for i in range(len(export_data['reports'])):
                    if 'data' in export_data['reports'][i]:
                        del export_data['reports'][i]['data']
            
            return export_data
        return {}
    
    @staticmethod
    def navigate_to(page: str):
        """
        Navega a una página SIN RERUN AUTOMÁTICO
        Solo cambia el estado, el rerun lo hace quien lo llama
        """
        st.session_state.current_page = page
        # NO hacer st.rerun() aquí - deja que el caller lo haga
    
    @staticmethod
    def get_current_page() -> str:
        """Obtiene la página actual"""
        return st.session_state.current_page