# Dashboard Component - Multi-user persistence with Supabase
import streamlit as st
import os
from src.services.session_manager import SessionManager
from datetime import datetime


def get_user_id() -> str:
    """Get current authenticated user ID"""
    user = st.session_state.get('user')
    if user:
        return user.id
    return None


def get_projects_from_supabase() -> list:
    """Fetch user's projects from Supabase"""
    user_id = get_user_id()
    if not user_id:
        return []

    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        projects = supabase.get_user_projects(user_id)
        return projects if projects else []
    except Exception as e:
        st.warning(f"Error loading projects: {e}")
        return []


def get_validations_from_supabase(limit: int = 10) -> list:
    """Fetch user's recent validations from Supabase"""
    user_id = get_user_id()
    if not user_id:
        return []

    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        validations = supabase.get_user_validations(user_id, limit=limit)
        return validations if validations else []
    except Exception as e:
        st.warning(f"Error loading validations: {e}")
        return []


def regenerate_pdf(validation_result: dict) -> bytes:
    """Regenerate PDF from stored validation result"""
    try:
        from src.utils.report_generator import ReportGenerator
        return ReportGenerator.generate_pdf(validation_result)
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None


def render_dashboard():
    """Renderiza el dashboard principal"""

    SessionManager.initialize()

    st.markdown("""
    <style>
        /* Dashboard Cards */
        .dashboard-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            transition: all 0.3s;
        }

        .dashboard-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #374151;
            margin-bottom: 0.5rem;
        }

        .card-value {
            font-size: 2rem;
            font-weight: 800;
            color: #10b981;
            margin: 0.5rem 0;
        }

        .card-subtitle {
            font-size: 0.9rem;
            color: #6b7280;
        }

        /* Progress Bar */
        .progress-container {
            background: #e5e7eb;
            border-radius: 8px;
            height: 8px;
            overflow: hidden;
            margin: 1rem 0;
        }

        .progress-bar {
            background: linear-gradient(90deg, #10b981, #14b8a6);
            height: 100%;
            transition: width 0.3s;
        }

        /* Stats */
        .stat-item {
            padding: 0.75rem;
            background: #f9fafb;
            border-radius: 8px;
            margin: 0.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header del dashboard - no project name as header
    st.markdown("## Dashboard")
    st.caption("Panel de control de Pyxten")

    st.divider()

    # Row 1: Validaciones Recientes (full width)
    render_recent_validations_card()

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Nueva Validacion and Mis Proyectos in same row
    col1, col2 = st.columns(2)

    with col1:
        render_nueva_validacion_button()

    with col2:
        render_mis_proyectos_card()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Row 3: Uso del Mes (full width below)
    render_usage_card()


def render_recent_validations_card():
    """Card de validaciones recientes con descripcion y PDF download"""

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Validaciones Recientes")

    # Fetch from Supabase if authenticated
    user_id = get_user_id()
    validations = []

    if user_id:
        validations = get_validations_from_supabase(limit=5)

    # Fallback to session history if no Supabase data
    if not validations:
        validations = SessionManager.get_validation_history()[:5]

    if validations:
        for i, val in enumerate(validations):
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 1])

                with col1:
                    # Handle both Supabase format and session format
                    address = val.get('property_address', val.get('result', {}).get('property_address', 'Sin direccion'))
                    st.markdown(f"**{address}**")

                    # Show project description
                    description = val.get('project_description', '')
                    if not description:
                        # Try to get from result object
                        description = val.get('result', {}).get('project_description', '')
                    if description:
                        truncated = description[:50] + '...' if len(description) > 50 else description
                        st.caption(f"Proyecto: {truncated}")

                    # Municipality and date
                    municipality = val.get('municipality', val.get('result', {}).get('municipality', ''))
                    timestamp = val.get('created_at', val.get('timestamp', ''))
                    if timestamp:
                        date_str = timestamp[:10] if isinstance(timestamp, str) else timestamp.strftime('%Y-%m-%d')
                    else:
                        date_str = ''
                    st.caption(f"{municipality} | {date_str}")

                with col2:
                    viable = val.get('viable', val.get('result', {}).get('viable', False))
                    if viable:
                        st.success("Viable")
                    else:
                        st.error("No Viable")

                with col3:
                    # PDF Download - regenerate from stored result
                    result_data = val.get('result', val)

                    if result_data:
                        pdf_bytes = regenerate_pdf(result_data)
                        if pdf_bytes:
                            st.download_button(
                                label="PDF",
                                data=pdf_bytes,
                                file_name=f"reporte_{i+1}.pdf",
                                mime="application/pdf",
                                key=f"download_recent_{i}_{val.get('id', i)}",
                                help="Descargar PDF"
                            )
                        else:
                            st.button(
                                "PDF",
                                disabled=True,
                                key=f"no_pdf_{i}_{val.get('id', i)}",
                                help="Reporte no disponible"
                            )
                    else:
                        st.button(
                            "PDF",
                            disabled=True,
                            key=f"no_result_{i}",
                            help="Datos no disponibles"
                        )

                if i < len(validations) - 1:
                    st.divider()
    else:
        st.info("No hay validaciones recientes. Crea tu primera validacion!")

        if st.button("Nueva Validacion", key="new_val_from_empty", use_container_width=True):
            st.session_state.current_page = 'homepage'
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_nueva_validacion_button():
    """Simple card with Nueva Validacion button"""

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)

    can_validate = SessionManager.can_validate()

    if can_validate:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #374151; margin-bottom: 1rem;">
                Nueva Validacion
            </div>
            <div style="color: #6b7280; margin-bottom: 1.5rem;">
                Valida tu proyecto de construccion
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "Comenzar Validacion",
            key="start_new_validation",
            type="primary",
            use_container_width=True
        ):
            st.session_state.current_page = 'homepage'
            st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444; margin-bottom: 1rem;">
                Limite Alcanzado
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.warning("Has alcanzado el limite de validaciones gratuitas este mes.")

        if st.button("Ver Planes", key="upgrade_from_nueva_val", use_container_width=True):
            st.session_state.current_page = 'pricing'
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_mis_proyectos_card():
    """Card showing user's projects list from Supabase"""

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)

    # Fetch projects from Supabase
    user_id = get_user_id()
    projects = []

    if user_id:
        projects = get_projects_from_supabase()

    # Fallback to session if no Supabase data
    if not projects:
        session_projects = SessionManager.get_all_projects()
        projects = list(session_projects.values()) if session_projects else []

    project_count = len(projects)

    st.markdown("### Mis Proyectos")

    if projects:
        # Show list of project names (folders)
        for proj in projects[:5]:  # Show first 5
            name = proj.get('name', 'Sin nombre')
            municipality = proj.get('municipality', '')
            st.markdown(f"""
            <div style="padding: 0.5rem; background: #f9fafb; border-radius: 6px; margin: 0.5rem 0; border-left: 3px solid #10b981;">
                <div style="font-weight: 600; color: #374151;">{name}</div>
                <div style="font-size: 0.8rem; color: #6b7280;">{municipality}</div>
            </div>
            """, unsafe_allow_html=True)

        if project_count > 5:
            st.caption(f"... y {project_count - 5} mas")
    else:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; color: #6b7280;">
            No tienes proyectos todavia
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; margin-top: 1rem;">
        <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
            {project_count}
        </div>
        <div style="font-size: 0.85rem; color: #6b7280;">
            proyecto{'s' if project_count != 1 else ''} guardado{'s' if project_count != 1 else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "Ver Todos los Proyectos",
        key="go_to_all_projects",
        use_container_width=True
    ):
        st.session_state.current_page = 'active_projects'
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_usage_card():
    """Card de uso mensual"""

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Uso del Mes")

    used = st.session_state.validation_count
    limit = st.session_state.validation_limit
    remaining = SessionManager.get_remaining_validations()

    # Barra de progreso
    percentage = (used / limit) * 100 if limit > 0 else 0

    st.markdown(f"""
    <div class="card-value">{used} / {limit}</div>
    <div class="card-subtitle">validaciones utilizadas</div>

    <div class="progress-container">
        <div class="progress-bar" style="width: {percentage}%;"></div>
    </div>
    """, unsafe_allow_html=True)

    if remaining > 0:
        st.success(f"Te quedan **{remaining}** validaciones gratuitas")
    else:
        st.error("Has usado todas tus validaciones gratuitas")

    st.divider()

    # Stats adicionales
    st.markdown("**Este Mes:**")

    # Get counts from Supabase if available
    user_id = get_user_id()
    projects = []
    validations = []

    if user_id:
        projects = get_projects_from_supabase()
        validations = get_validations_from_supabase(limit=100)
    else:
        projects = list(SessionManager.get_all_projects().values())
        validations = SessionManager.get_validation_history()

    project_count = len(projects)
    viable_count = sum(1 for v in validations if v.get('viable', v.get('result', {}).get('viable', False)))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="stat-item">
            <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                {project_count}
            </div>
            <div style="font-size: 0.85rem; color: #6b7280;">
                Proyectos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-item">
            <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                {viable_count}
            </div>
            <div style="font-size: 0.85rem; color: #6b7280;">
                Viables
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
