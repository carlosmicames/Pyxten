import streamlit as st
import os
from datetime import datetime


def check_validation_limit(user_id: str) -> dict:
    """
    Check if user can perform validation

    Returns:
        {
            "can_validate": bool,
            "remaining": int,
            "used": int,
            "limit": int,
            "tier": str
        }
    """

    # If Supabase not configured, use session-based tracking
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        return _check_session_limit()

    try:
        from src.services.supabase_client import SupabaseService

        supabase = SupabaseService()

        # Get current period (YYYY-MM)
        period = datetime.now().strftime("%Y-%m")

        # Get user tier
        tier = supabase.get_user_tier(user_id)

        # Get remaining validations
        remaining = supabase.get_remaining_validations(user_id, period, tier)

        limits = {
            'free': 5,
            'professional': 999999,
            'enterprise': 999999
        }

        limit = limits.get(tier, 5)
        used = limit - remaining

        return {
            "can_validate": remaining > 0,
            "remaining": remaining,
            "used": used,
            "limit": limit,
            "tier": tier
        }

    except Exception as e:
        # Fallback to session-based tracking
        return _check_session_limit()


def _check_session_limit() -> dict:
    """Fallback: Check validation limit using session state"""

    if 'validations_used' not in st.session_state:
        st.session_state.validations_used = 0

    limit = 5
    used = st.session_state.validations_used
    remaining = max(0, limit - used)

    return {
        "can_validate": remaining > 0,
        "remaining": remaining,
        "used": used,
        "limit": limit,
        "tier": "free"
    }


def increment_usage(user_id: str):
    """Increment validation count after successful validation"""

    # Always increment session state as backup
    if 'validations_used' not in st.session_state:
        st.session_state.validations_used = 0
    st.session_state.validations_used += 1

    # If Supabase configured, also update there
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        try:
            from src.services.supabase_client import SupabaseService

            supabase = SupabaseService()
            period = datetime.now().strftime("%Y-%m")
            supabase.increment_validation_count(user_id, period)

        except Exception:
            pass  # Session state already updated


def render_usage_warning(usage_info: dict) -> bool:
    """
    Display usage warning to user

    Returns:
        True if user can continue, False if blocked
    """

    remaining = usage_info['remaining']

    if remaining <= 0:
        st.error("""
        ### Limite Alcanzado

        Has usado todas tus validaciones gratuitas este mes (5/5).

        **Actualiza a Plan Profesional para:**
        - Validaciones Fase 1 ilimitadas
        - 10 validaciones PCOC/mes
        - Memorial Explicativo con IA
        - Proyectos guardados en base de datos
        """)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Ver Planes y Precios", type="primary", use_container_width=True):
                st.session_state.current_page = 'pricing'
                st.rerun()

        return False

    elif remaining <= 2:
        st.warning(f"Te quedan {remaining} validaciones gratuitas este mes")

    return True


def render_usage_badge(usage_info: dict):
    """Render a small usage badge in sidebar"""

    remaining = usage_info['remaining']
    limit = usage_info['limit']
    tier = usage_info['tier']

    if tier == 'free':
        st.caption(f"Validaciones: {remaining}/{limit}")
    else:
        st.caption(f"Plan: {tier.capitalize()}")
