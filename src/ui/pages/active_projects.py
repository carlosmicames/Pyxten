# Pagina de proyectos activos - Multi-user persistence with Supabase
import streamlit as st
import os
from src.services.session_manager import SessionManager


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
        return None

    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        projects = supabase.get_user_projects(user_id)
        return projects if projects else []
    except Exception as e:
        st.warning(f"Error loading projects from database: {e}")
        return None


def create_project_in_supabase(name: str, address: str, municipality: str) -> dict:
    """Create a new project in Supabase"""
    user_id = get_user_id()
    if not user_id:
        return None

    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()

        project_data = {
            'name': name,
            'address': address if address else "",
            'municipality': municipality if municipality else "",
            'catastro_number': None,
            'calificacion': None,
            'zoning_code': None
        }

        created = supabase.create_project(user_id, project_data)
        return created
    except Exception as e:
        st.warning(f"Error creating project in database: {e}")
        return None


def delete_project_from_supabase(project_id: str) -> bool:
    """Delete a project from Supabase"""
    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        supabase.delete_project(project_id)
        return True
    except Exception as e:
        st.warning(f"Error deleting project: {e}")
        return False


def update_project_in_supabase(project_id: str, updates: dict) -> bool:
    """Update a project in Supabase"""
    try:
        from src.services.supabase_client import SupabaseService
        supabase = SupabaseService()
        supabase.update_project(project_id, updates)
        return True
    except Exception as e:
        st.warning(f"Error updating project: {e}")
        return False


def _normalize_project(project: dict) -> dict:
    """Normalize project data from Supabase to match SessionManager format"""
    normalized = project.copy()

    # Handle date field differences
    if 'created_at' in normalized and 'created_date' not in normalized:
        normalized['created_date'] = normalized['created_at']

    if 'updated_at' in normalized and 'last_modified' not in normalized:
        normalized['last_modified'] = normalized['updated_at']

    # Ensure required fields have defaults
    if 'status' not in normalized:
        normalized['status'] = 'En Progreso'

    if 'documents' not in normalized:
        normalized['documents'] = {}

    if 'reports' not in normalized:
        normalized['reports'] = []

    return normalized


def render_active_projects_page():
    """Pagina dedicada para ver y gestionar proyectos activos"""

    SessionManager.initialize()

    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827;">
            Proyectos
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Gestiona y monitorea tus proyectos y validaciones
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch projects from Supabase (primary source)
    user_id = get_user_id()
    projects = {}
    use_supabase = False

    if user_id:
        supabase_projects = get_projects_from_supabase()
        if supabase_projects is not None:
            # Convert to dict format and normalize
            projects = {p['id']: _normalize_project(p) for p in supabase_projects}
            use_supabase = True

    # Fallback to SessionManager if no Supabase data
    if not projects and not use_supabase:
        projects = SessionManager.get_all_projects()

    # Add "Nueva Carpeta" button at the top
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("+ Nueva Carpeta", type="primary", key="create_new_folder_btn"):
            st.session_state.show_create_folder_modal = True
            st.rerun()

    # Create folder modal
    if st.session_state.get('show_create_folder_modal'):
        render_create_folder_modal(use_supabase)

    st.markdown("<br>", unsafe_allow_html=True)

    if not projects:
        # Empty state
        st.markdown("""
        <div style="background: white; padding: 3rem; border-radius: 16px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); text-align: center;
                    max-width: 600px; margin: 2rem auto;">
            <h2 style="color: #374151; margin-bottom: 1rem;">
                No tienes proyectos todavia
            </h2>
            <p style="color: #6b7280; font-size: 1.1rem; margin-bottom: 2rem;">
                Usa el boton "+ Nueva Carpeta" arriba para crear tu primer proyecto,
                o realiza una validacion y guardala en un nuevo proyecto.
            </p>
        </div>
        """, unsafe_allow_html=True)

        return

    # Stats bar
    active_projects = [p for p in projects.values() if p.get('status') == 'En Progreso']
    completed_projects = [p for p in projects.values() if p.get('status') == 'Completado']

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; font-weight: 800; color: #10b981;">
                {len(projects)}
            </div>
            <div style="color: #6b7280; font-size: 0.9rem;">
                Total Proyectos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; font-weight: 800; color: #f59e0b;">
                {len(active_projects)}
            </div>
            <div style="color: #6b7280; font-size: 0.9rem;">
                En Progreso
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; font-weight: 800; color: #3b82f6;">
                {len(completed_projects)}
            </div>
            <div style="color: #6b7280; font-size: 0.9rem;">
                Completados
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        phase1_completed = sum(1 for p in projects.values() if p.get('phase1_completed'))
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; font-weight: 800; color: #8b5cf6;">
                {phase1_completed}
            </div>
            <div style="color: #6b7280; font-size: 0.9rem;">
                Fase 1 Validada
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Filter/Sort options
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        filter_status = st.selectbox(
            "Filtrar por Estado",
            options=["Todos", "En Progreso", "Completado", "Pausado"]
        )

    with col2:
        sort_by = st.selectbox(
            "Ordenar por",
            options=["Mas reciente", "Mas antiguo", "Nombre A-Z", "Nombre Z-A"]
        )

    with col3:
        if st.button("+ Nuevo Proyecto", use_container_width=True, key="new_project_btn_inline"):
            st.session_state.show_create_folder_modal = True
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter projects
    filtered_projects = list(projects.values())

    if filter_status != "Todos":
        filtered_projects = [p for p in filtered_projects if p.get('status') == filter_status]

    # Sort projects
    if sort_by == "Mas reciente":
        filtered_projects.sort(key=lambda p: p.get('created_date', ''), reverse=True)
    elif sort_by == "Mas antiguo":
        filtered_projects.sort(key=lambda p: p.get('created_date', ''))
    elif sort_by == "Nombre A-Z":
        filtered_projects.sort(key=lambda p: p.get('name', ''))
    elif sort_by == "Nombre Z-A":
        filtered_projects.sort(key=lambda p: p.get('name', ''), reverse=True)

    # Display projects
    if not filtered_projects:
        st.info(f"No hay proyectos con estado '{filter_status}'")
    else:
        for project in filtered_projects:
            render_project_card(project, use_supabase)


def render_project_card(project, use_supabase: bool = False):
    """Renderiza una tarjeta de proyecto con acciones"""

    # Status badge color
    status_colors = {
        'En Progreso': ('#f59e0b', '#fef3c7'),
        'Completado': ('#10b981', '#d1fae5'),
        'Pausado': ('#ef4444', '#fee2e2')
    }

    badge_color, bg_color = status_colors.get(project.get('status', 'En Progreso'), ('#6b7280', '#f3f4f6'))

    st.markdown(f"""
    <div style="background: white; padding: 1.5rem; border-radius: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1.5rem;
                border-left: 4px solid {badge_color};">
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        st.markdown(f"""
        <div style="margin-bottom: 0.5rem;">
            <span style="background: {bg_color}; color: {badge_color};
                        padding: 0.25rem 0.75rem; border-radius: 12px;
                        font-size: 0.8rem; font-weight: 600;">
                {project.get('status', 'En Progreso')}
            </span>
        </div>
        <h3 style="margin: 0.5rem 0; color: #111827; font-size: 1.3rem;">
            {project.get('name', 'Sin nombre')}
        </h3>
        <p style="color: #6b7280; margin: 0.25rem 0; font-size: 0.9rem;">
            {project.get('address', '')}
        </p>
        <p style="color: #9ca3af; margin: 0.25rem 0; font-size: 0.85rem;">
            {project.get('municipality', '')}
        </p>
        """, unsafe_allow_html=True)

    with col2:
        # Project progress
        phase1_done = project.get('phase1_completed', False)
        phase1_icon = "OK" if phase1_done else "Pendiente"
        docs_count = len(project.get('documents', {}))
        reports_count = len(project.get('reports', []))
        created_date = project.get('created_date', project.get('created_at', ''))[:10] if project.get('created_date') or project.get('created_at') else ''

        st.markdown(f"""
        <div style="font-size: 0.9rem; color: #6b7280;">
            <strong>Fase 1:</strong> {phase1_icon}<br>
            <strong>Documentos:</strong> {docs_count}<br>
            <strong>Reportes:</strong> {reports_count}<br>
            <strong>Creado:</strong> {created_date}
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Actions
        project_id = project.get('id')

        if st.button("Ver Detalles", key=f"view_{project_id}", use_container_width=True):
            SessionManager.set_current_project(project_id)
            st.success(f"Proyecto '{project.get('name')}' seleccionado")
            st.rerun()

        if st.button("Editar", key=f"edit_{project_id}", use_container_width=True):
            st.session_state[f"editing_{project_id}"] = True
            st.rerun()

        # Delete with confirmation
        if st.session_state.get(f"confirm_delete_{project_id}", False):
            if st.button("Confirmar Eliminar", key=f"confirm_del_{project_id}",
                        use_container_width=True, type="primary"):
                # Delete from Supabase if using it
                if use_supabase:
                    delete_project_from_supabase(project_id)

                # Also delete from session
                SessionManager.delete_project(project_id)
                st.session_state[f"confirm_delete_{project_id}"] = False
                st.success("Proyecto eliminado")
                st.rerun()
        else:
            if st.button("Eliminar", key=f"delete_{project_id}", use_container_width=True):
                st.session_state[f"confirm_delete_{project_id}"] = True
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Edit form (if editing)
    if st.session_state.get(f"editing_{project_id}", False):
        with st.expander("Editar Proyecto", expanded=True):
            with st.form(f"edit_form_{project_id}"):
                new_name = st.text_input("Nombre", value=project.get('name', ''))
                new_status = st.selectbox(
                    "Estado",
                    options=['En Progreso', 'Completado', 'Pausado'],
                    index=['En Progreso', 'Completado', 'Pausado'].index(project.get('status', 'En Progreso'))
                )
                new_notes = st.text_area("Notas", value=project.get('notes', ''), height=100)

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Guardar", use_container_width=True, type="primary"):
                        updates = {
                            'name': new_name,
                            'status': new_status,
                            'notes': new_notes
                        }

                        # Update in Supabase if using it
                        if use_supabase:
                            update_project_in_supabase(project_id, updates)

                        # Also update in session
                        SessionManager.update_project(project_id, updates)
                        st.session_state[f"editing_{project_id}"] = False
                        st.success("Proyecto actualizado")
                        st.rerun()

                with col2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state[f"editing_{project_id}"] = False
                        st.rerun()

    # Show details if it's the current project
    current_project = SessionManager.get_current_project()
    if current_project and current_project.get('id') == project_id:
        with st.expander("Detalles Completos", expanded=False):
            render_full_project_details(project)


def render_full_project_details(project):
    """Muestra detalles completos del proyecto"""

    tab1, tab2, tab3 = st.tabs(["Informacion", "Documentos", "Reportes"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Informacion General**")
            st.write(f"**ID:** `{project.get('id')}`")
            st.write(f"**Nombre:** {project.get('name')}")
            st.write(f"**Direccion:** {project.get('address')}")
            st.write(f"**Municipio:** {project.get('municipality')}")

        with col2:
            st.markdown("**Estado del Proyecto**")
            st.write(f"**Estado:** {project.get('status')}")
            phase1_status = 'Completada' if project.get('phase1_completed') else 'Pendiente'
            st.write(f"**Fase 1:** {phase1_status}")
            created = project.get('created_date', project.get('created_at', ''))[:10] if project.get('created_date') or project.get('created_at') else ''
            modified = project.get('last_modified', project.get('updated_at', ''))[:10] if project.get('last_modified') or project.get('updated_at') else ''
            st.write(f"**Creado:** {created}")
            st.write(f"**Modificado:** {modified}")

        if project.get('notes'):
            st.markdown("**Notas:**")
            st.info(project['notes'])

    with tab2:
        if project.get('documents'):
            st.markdown("**Documentos Subidos:**")
            for doc_type, doc_info in project['documents'].items():
                st.markdown(f"- **{doc_type}:** `{doc_info.get('filename', 'Sin nombre')}`")
                uploaded = doc_info.get('uploaded_date', '')[:10] if doc_info.get('uploaded_date') else ''
                st.caption(f"Subido: {uploaded}")
        else:
            st.info("No hay documentos subidos en este proyecto")

    with tab3:
        if project.get('reports'):
            st.markdown("**Reportes Generados:**")
            for i, report in enumerate(project['reports']):
                col1, col2 = st.columns([3, 1])
                with col1:
                    generated = report.get('generated_date', '')[:10] if report.get('generated_date') else ''
                    st.write(f"**{report.get('type', 'Reporte')}** - {generated}")
                with col2:
                    if report.get('data'):
                        st.download_button(
                            label="Descargar",
                            data=report['data'],
                            file_name=f"{report.get('type', 'reporte')}_{i}.pdf",
                            mime="application/pdf",
                            key=f"dl_report_{project.get('id')}_{i}"
                        )
        else:
            st.info("No hay reportes generados para este proyecto")


def render_create_folder_modal(use_supabase: bool = False):
    """Render modal to create a new project folder"""
    st.markdown("### Crear Nueva Carpeta")

    with st.form("create_folder_form"):
        folder_name = st.text_input(
            "Nombre de la carpeta *",
            placeholder="Ej: Cliente ABC - Proyecto Residencial",
            help="Nombre descriptivo para identificar el proyecto"
        )

        folder_address = st.text_input(
            "Direccion (opcional)",
            placeholder="Ej: Calle Luna 123, Urb. San Patricio",
            help="Direccion de la propiedad principal"
        )

        from src.database.rules_loader import RulesDatabase
        rules_db = RulesDatabase()

        folder_municipality = st.selectbox(
            "Municipio (opcional)",
            options=[""] + rules_db.get_municipalities(),
            help="Municipio donde se ubica la propiedad"
        )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button(
                "Crear Carpeta",
                type="primary",
                use_container_width=True
            )

        with col2:
            cancel = st.form_submit_button(
                "Cancelar",
                use_container_width=True
            )

        if submitted:
            if folder_name:
                user_id = get_user_id()

                # Create in Supabase FIRST if authenticated (primary source)
                if user_id:
                    created = create_project_in_supabase(
                        name=folder_name,
                        address=folder_address if folder_address else "",
                        municipality=folder_municipality if folder_municipality else ""
                    )

                    if created:
                        st.success(f"Carpeta '{folder_name}' creada exitosamente")
                        st.session_state.show_create_folder_modal = False
                        st.rerun()
                    else:
                        # Fallback to session if Supabase fails
                        SessionManager.create_project(
                            name=folder_name,
                            address=folder_address if folder_address else "",
                            municipality=folder_municipality if folder_municipality else ""
                        )
                        st.success(f"Carpeta '{folder_name}' creada localmente")
                        st.session_state.show_create_folder_modal = False
                        st.rerun()
                else:
                    # No auth - create in session only
                    SessionManager.create_project(
                        name=folder_name,
                        address=folder_address if folder_address else "",
                        municipality=folder_municipality if folder_municipality else ""
                    )
                    st.success(f"Carpeta '{folder_name}' creada exitosamente")
                    st.session_state.show_create_folder_modal = False
                    st.rerun()
            else:
                st.error("Por favor ingresa un nombre para la carpeta")

        if cancel:
            st.session_state.show_create_folder_modal = False
            st.rerun()
