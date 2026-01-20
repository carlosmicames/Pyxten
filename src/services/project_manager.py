# Project Manager Service - Manages project folders and validations
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import streamlit as st


class ProjectManager:
    """
    Manages project folders and validations with Supabase + SessionManager fallback.

    Project folders contain validations, each with:
    - Validation data (result from ZoningValidator)
    - PDF bytes (generated report)
    - Metadata (address, municipality, date, viable status)
    """

    def __init__(self):
        self.use_supabase = self._check_supabase_available()

    def _check_supabase_available(self) -> bool:
        """Check if Supabase is configured and user is authenticated"""
        return (
            os.getenv("SUPABASE_URL") and
            os.getenv("SUPABASE_KEY") and
            st.session_state.get('user') is not None
        )

    def _get_supabase_client(self):
        """Get Supabase client if available"""
        if self.use_supabase:
            try:
                from src.services.supabase_client import SupabaseService
                return SupabaseService()
            except Exception:
                return None
        return None

    def _generate_id(self) -> str:
        """Generate a unique ID for folders/validations"""
        return f"folder_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def create_folder(self, folder_name: str, user_id: Optional[str] = None) -> str:
        """
        Create a new project folder.

        Args:
            folder_name: Name of the folder
            user_id: Optional user ID for Supabase

        Returns:
            folder_id: The ID of the created folder
        """
        folder_id = self._generate_id()

        folder_data = {
            'id': folder_id,
            'name': folder_name,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'validations': [],
            'status': 'En Progreso'
        }

        # Try Supabase first
        if self.use_supabase and user_id:
            supabase = self._get_supabase_client()
            if supabase:
                try:
                    # Create project in Supabase
                    project = supabase.create_project(user_id, {
                        'name': folder_name,
                        'address': '',
                        'municipality': '',
                        'notes': 'Carpeta de proyecto'
                    })
                    if project:
                        return project['id']
                except Exception as e:
                    st.warning(f"Error creating folder in Supabase: {e}")

        # Fallback to session state
        if 'project_folders' not in st.session_state:
            st.session_state.project_folders = {}

        st.session_state.project_folders[folder_id] = folder_data
        return folder_id

    def add_validation_to_folder(
        self,
        folder_id: str,
        validation_data: dict,
        pdf_bytes: bytes,
        address: str = '',
        municipality: str = ''
    ) -> str:
        """
        Add a validation to a project folder.

        Args:
            folder_id: The folder ID
            validation_data: The validation result from ZoningValidator
            pdf_bytes: The generated PDF report
            address: Property address
            municipality: Municipality name

        Returns:
            validation_id: The ID of the added validation
        """
        validation_id = f"val_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        validation_entry = {
            'id': validation_id,
            'folder_id': folder_id,
            'data': validation_data,
            'pdf': pdf_bytes,
            'address': address or validation_data.get('property_address', ''),
            'municipality': municipality or validation_data.get('municipality', ''),
            'viable': validation_data.get('viable', False),
            'created_at': datetime.now().isoformat()
        }

        # Try Supabase first
        if self.use_supabase:
            supabase = self._get_supabase_client()
            if supabase:
                try:
                    # Add report to project in Supabase
                    from src.services.session_manager import SessionManager
                    SessionManager.add_report_to_project(folder_id, 'fase1', pdf_bytes)
                    SessionManager.update_project(folder_id, {
                        'phase1_completed': True,
                        'phase1_result': validation_data
                    })
                    return validation_id
                except Exception as e:
                    st.warning(f"Error adding validation to Supabase: {e}")

        # Fallback to session state
        if 'project_folders' not in st.session_state:
            st.session_state.project_folders = {}

        if folder_id in st.session_state.project_folders:
            st.session_state.project_folders[folder_id]['validations'].append(validation_entry)
            st.session_state.project_folders[folder_id]['updated_at'] = datetime.now().isoformat()
        else:
            # Create folder if doesn't exist
            st.session_state.project_folders[folder_id] = {
                'id': folder_id,
                'name': f"Proyecto {folder_id[-8:]}",
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'validations': [validation_entry],
                'status': 'En Progreso'
            }

        return validation_id

    def get_user_folders(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all folders for a user.

        Args:
            user_id: Optional user ID for Supabase

        Returns:
            List of folder dictionaries
        """
        folders = []

        # Try Supabase first
        if self.use_supabase and user_id:
            supabase = self._get_supabase_client()
            if supabase:
                try:
                    projects = supabase.get_user_projects(user_id)
                    if projects:
                        for p in projects:
                            folders.append({
                                'id': p['id'],
                                'name': p['name'],
                                'created_at': p.get('created_at', ''),
                                'updated_at': p.get('updated_at', ''),
                                'validations': p.get('reports', []),
                                'status': p.get('status', 'En Progreso'),
                                'phase1_completed': p.get('phase1_completed', False)
                            })
                        return folders
                except Exception:
                    pass

        # Fallback to session state
        if 'project_folders' in st.session_state:
            folders = list(st.session_state.project_folders.values())

        return folders

    def get_folder_validations(self, folder_id: str) -> List[Dict]:
        """
        Get all validations in a folder.

        Args:
            folder_id: The folder ID

        Returns:
            List of validation dictionaries
        """
        # Try session state first (has full data)
        if 'project_folders' in st.session_state:
            folder = st.session_state.project_folders.get(folder_id)
            if folder:
                return folder.get('validations', [])

        # Try Supabase
        if self.use_supabase:
            supabase = self._get_supabase_client()
            if supabase:
                try:
                    # Get project reports from Supabase
                    from src.services.session_manager import SessionManager
                    projects = SessionManager.get_all_projects()
                    if folder_id in projects:
                        return projects[folder_id].get('reports', [])
                except Exception:
                    pass

        return []

    def delete_folder(self, folder_id: str) -> bool:
        """
        Delete a project folder.

        Args:
            folder_id: The folder ID

        Returns:
            True if deleted successfully
        """
        # Delete from session state
        if 'project_folders' in st.session_state:
            if folder_id in st.session_state.project_folders:
                del st.session_state.project_folders[folder_id]
                return True

        # Try Supabase
        if self.use_supabase:
            try:
                from src.services.session_manager import SessionManager
                SessionManager.delete_project(folder_id)
                return True
            except Exception:
                pass

        return False

    def rename_folder(self, folder_id: str, new_name: str) -> bool:
        """
        Rename a project folder.

        Args:
            folder_id: The folder ID
            new_name: New name for the folder

        Returns:
            True if renamed successfully
        """
        # Rename in session state
        if 'project_folders' in st.session_state:
            if folder_id in st.session_state.project_folders:
                st.session_state.project_folders[folder_id]['name'] = new_name
                st.session_state.project_folders[folder_id]['updated_at'] = datetime.now().isoformat()
                return True

        # Try Supabase
        if self.use_supabase:
            try:
                from src.services.session_manager import SessionManager
                SessionManager.update_project(folder_id, {'name': new_name})
                return True
            except Exception:
                pass

        return False

    def get_folder_by_id(self, folder_id: str) -> Optional[Dict]:
        """
        Get a specific folder by ID.

        Args:
            folder_id: The folder ID

        Returns:
            Folder dictionary or None
        """
        # Check session state first
        if 'project_folders' in st.session_state:
            folder = st.session_state.project_folders.get(folder_id)
            if folder:
                return folder

        # Try SessionManager (for backwards compatibility)
        from src.services.session_manager import SessionManager
        projects = SessionManager.get_all_projects()
        return projects.get(folder_id)
