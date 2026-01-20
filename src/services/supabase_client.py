import os
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime

class SupabaseService:
    """Supabase database service"""

    def __init__(self):
        # Try st.secrets first (Streamlit Cloud), then env vars
        url = None
        key = None

        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass

        if not url:
            url = os.getenv("SUPABASE_URL")
        if not key:
            key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or st.secrets")

        try:
            from supabase import create_client, Client
            self.client: Client = create_client(url, key)
        except ImportError:
            raise ImportError("supabase package not installed. Run: pip install supabase")

    # ========================================================================
    # PROJECTS
    # ========================================================================

    def create_project(self, user_id: str, project_data: Dict) -> Dict:
        """Create a new project"""

        data = {
            "user_id": user_id,
            "name": project_data['name'],
            "address": project_data['address'],
            "municipality": project_data['municipality'],
            "catastro_number": project_data.get('catastro_number'),
            "calificacion": project_data.get('calificacion'),
            "zoning_code": project_data.get('zoning_code'),
            "status": "En Progreso"
        }

        result = self.client.table('projects').insert(data).execute()
        return result.data[0] if result.data else None

    def get_user_projects(self, user_id: str) -> List[Dict]:
        """Get all projects for a user"""

        result = self.client.table('projects').select("*").eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data if result.data else []

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a specific project"""

        result = self.client.table('projects').select("*").eq('id', project_id).execute()
        return result.data[0] if result.data else None

    def update_project(self, project_id: str, updates: Dict) -> Dict:
        """Update a project"""

        result = self.client.table('projects').update(updates).eq('id', project_id).execute()
        return result.data[0] if result.data else None

    def delete_project(self, project_id: str):
        """Delete a project"""

        self.client.table('projects').delete().eq('id', project_id).execute()

    # ========================================================================
    # VALIDATIONS
    # ========================================================================

    def create_validation(self, user_id: str, validation_data: Dict) -> Dict:
        """Create a validation record with full result storage for PDF regeneration"""

        # Extract key fields for easy querying
        result_obj = validation_data.get('result', {})

        data = {
            "user_id": user_id,
            "project_id": validation_data.get('project_id'),
            "validation_type": validation_data.get('type', 'fase1'),  # 'fase1' or 'pcoc'
            "result": result_obj,  # JSONB - full result for PDF regeneration
            "viable": result_obj.get('viable', False),
            "project_description": validation_data.get('project_description', ''),
            "property_address": result_obj.get('property_address', ''),
            "municipality": result_obj.get('municipality', '')
        }

        result = self.client.table('validations').insert(data).execute()
        return result.data[0] if result.data else None

    def get_user_validations(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent validations for a user"""

        result = self.client.table('validations').select("*").eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []

    def get_project_validations(self, project_id: str) -> List[Dict]:
        """Get all validations for a project"""

        result = self.client.table('validations').select("*").eq('project_id', project_id).order('created_at', desc=True).execute()
        return result.data if result.data else []

    def get_validation_by_id(self, validation_id: str) -> Optional[Dict]:
        """Get a specific validation by ID"""

        result = self.client.table('validations').select("*").eq('id', validation_id).execute()
        return result.data[0] if result.data else None

    # ========================================================================
    # USAGE TRACKING
    # ========================================================================

    def get_or_create_usage(self, user_id: str, period: str) -> Dict:
        """Get or create usage record for current period"""

        # Try to get existing
        result = self.client.table('usage_tracking').select("*").eq('user_id', user_id).eq('period', period).execute()

        if result.data:
            return result.data[0]

        # Create new
        data = {
            "user_id": user_id,
            "period": period,
            "validations_used": 0,
            "tier": "free"
        }

        result = self.client.table('usage_tracking').insert(data).execute()
        return result.data[0] if result.data else None

    def increment_validation_count(self, user_id: str, period: str):
        """Increment validation count for user in current period"""

        usage = self.get_or_create_usage(user_id, period)

        new_count = usage['validations_used'] + 1

        self.client.table('usage_tracking').update({
            'validations_used': new_count
        }).eq('id', usage['id']).execute()

    def get_remaining_validations(self, user_id: str, period: str, tier: str = 'free') -> int:
        """Get remaining validations for user"""

        limits = {
            'free': 5,
            'professional': 999999,  # Unlimited Fase 1
            'enterprise': 999999
        }

        usage = self.get_or_create_usage(user_id, period)
        used = usage['validations_used']
        limit = limits.get(tier, 5)

        return max(0, limit - used)

    def get_user_tier(self, user_id: str) -> str:
        """Get user's subscription tier"""

        # Try to get from subscriptions table
        try:
            result = self.client.table('subscriptions').select("tier").eq('user_id', user_id).eq('status', 'active').execute()
            if result.data:
                return result.data[0].get('tier', 'free')
        except Exception:
            pass

        return 'free'

    # ========================================================================
    # ADMIN STATS
    # ========================================================================

    def get_total_projects_count(self) -> int:
        """Get total number of projects"""
        result = self.client.table('projects').select('id', count='exact').execute()
        return result.count if hasattr(result, 'count') else 0

    def get_total_validations_count(self) -> int:
        """Get total number of validations"""
        result = self.client.table('validations').select('id', count='exact').execute()
        return result.count if hasattr(result, 'count') else 0

    def get_month_validations_count(self, period: str) -> int:
        """Get validations count for a specific month"""
        result = self.client.table('usage_tracking').select('validations_used').eq('period', period).execute()
        if result.data:
            return sum(u['validations_used'] for u in result.data)
        return 0

    def get_all_projects(self, limit: int = 100) -> List[Dict]:
        """Get all projects (admin)"""
        result = self.client.table('projects').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []

    def get_all_validations(self, limit: int = 100) -> List[Dict]:
        """Get all validations (admin)"""
        result = self.client.table('validations').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []
