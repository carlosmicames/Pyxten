import streamlit as st
import os
from datetime import datetime

# IMPORTANT: Set your admin user ID here after creating account
ADMIN_USERS = [1378101c-24a6-470f-ad05-cfe98847a46f]
    # Add your Supabase user ID here after signup
    # Example: "abc123-def456-ghi789"


def is_admin(user_id: str) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USERS


def render_admin_dashboard():
    """Admin dashboard with stats and all projects"""

    # Check if user is authenticated
    user = st.session_state.get('user')

    if not user:
        st.error("Acceso denegado - Debes iniciar sesion")
        return

    user_id = user.id

    if not is_admin(user_id):
        st.error("Acceso denegado - Solo administradores")
        st.info("Si eres administrador, agrega tu User ID a ADMIN_USERS en src/ui/pages/admin.py")
        st.code(f"Tu User ID: {user_id}")
        return

    st.markdown("## Panel de Administracion")

    # Check Supabase configuration
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        st.warning("Supabase no configurado. Mostrando datos de sesion.")
        _render_session_stats()
        return

    try:
        from src.services.supabase_client import SupabaseService

        supabase = SupabaseService()

        # Stats row
        col1, col2, col3, col4 = st.columns(4)

        # Get stats from Supabase
        total_projects = supabase.get_total_projects_count()
        total_validations = supabase.get_total_validations_count()
        period = datetime.now().strftime("%Y-%m")
        month_validations = supabase.get_month_validations_count(period)

        with col1:
            st.metric("Total Proyectos", total_projects)

        with col2:
            st.metric("Validaciones (Total)", total_validations)

        with col3:
            st.metric("Validaciones (Este Mes)", month_validations)

        with col4:
            st.metric("Periodo", period)

        st.divider()

        # All Projects Table
        st.markdown("### Todos los Proyectos")

        projects = supabase.get_all_projects(limit=50)

        if projects:
            import pandas as pd

            df = pd.DataFrame(projects)

            # Select columns to display
            display_cols = ['name', 'municipality', 'status', 'user_id', 'created_at']
            available_cols = [c for c in display_cols if c in df.columns]

            if available_cols:
                df_display = df[available_cols]
            else:
                df_display = df

            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No hay proyectos todavia")

        st.divider()

        # Recent Validations
        st.markdown("### Validaciones Recientes")

        validations = supabase.get_all_validations(limit=20)

        if validations:
            import pandas as pd

            df = pd.DataFrame(validations)

            # Select columns to display
            display_cols = ['validation_type', 'viable', 'user_id', 'created_at']
            available_cols = [c for c in display_cols if c in df.columns]

            if available_cols:
                df_display = df[available_cols]
            else:
                df_display = df

            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No hay validaciones todavia")

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.exception(e)


def _render_session_stats():
    """Render stats from session state when Supabase not available"""

    col1, col2, col3 = st.columns(3)

    with col1:
        projects = st.session_state.get('projects', [])
        st.metric("Proyectos (Sesion)", len(projects))

    with col2:
        history = st.session_state.get('validation_history', [])
        st.metric("Validaciones (Sesion)", len(history))

    with col3:
        used = st.session_state.get('validations_used', 0)
        st.metric("Validaciones Usadas", f"{used}/5")

    st.info("Conecta Supabase para persistir datos entre sesiones")
