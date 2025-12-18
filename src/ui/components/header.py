# Header Component - FINAL: Logo pequeño izquierda, nav derecha, sin emojis
import streamlit as st
from src.services.session_manager import SessionManager

def render_header():
    """Renderiza el header con logo pequeño y navegación limpia"""
    
    SessionManager.initialize()
    
    # CSS para header horizontal
    st.markdown("""
    <style>
        /* Header horizontal */
        .pyxten-header-horizontal {
            background: white;
            border-bottom: 2px solid #e5e7eb;
            padding: 0.75rem 2rem;
            margin: -1rem -1rem 2rem -1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        /* Logo pequeño */
        .logo-small {
            font-size: 1.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        .tagline-small {
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 0.15rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header HTML
    st.markdown("""
    <div class="pyxten-header-horizontal">
        <div>
            <div class="logo-small">Pyxten</div>
            <div class="tagline-small">Validación Inteligente de Permisos</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navegación limpia en columns (Dashboard, Proyectos, Precios)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
    
    current_page = SessionManager.get_current_page()
    
    with col1:
        if st.button(
            "Dashboard", 
            key="nav_dashboard",
            type="primary" if current_page == "dashboard" else "secondary",
            use_container_width=True
        ):
            st.session_state.current_page = 'dashboard'
            st.rerun()
    
    with col2:
        if st.button(
            "Proyectos", 
            key="nav_projects",
            type="primary" if current_page == "projects" else "secondary",
            use_container_width=True
        ):
            if 'show_projects_menu' not in st.session_state:
                st.session_state.show_projects_menu = False
            st.session_state.show_projects_menu = not st.session_state.show_projects_menu
            st.rerun()
    
    with col3:
        if st.button(
            "Precios", 
            key="nav_pricing",
            type="primary" if current_page == "pricing" else "secondary",
            use_container_width=True
        ):
            st.session_state.current_page = 'pricing'
            st.rerun()
    
    # Dropdown de Proyectos
    if st.session_state.get('show_projects_menu', False):
        render_projects_dropdown()


def render_projects_dropdown():
    """Menú dropdown de proyectos"""
    
    with st.expander("Gestión de Proyectos", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Nuevo", "Activos", "Archivos"])
        
        with tab1:
            render_new_project_form()
        
        with tab2:
            render_active_projects_list()
        
        with tab3:
            render_project_files()


def render_new_project_form():
    """Formulario para crear nuevo proyecto"""
    
    st.markdown("### Crear Nuevo Proyecto")
    
    with st.form("quick_new_project"):
        project_name = st.text_input(
            "Nombre del Proyecto",
            placeholder="Ej: Residencia Familia García"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            project_address = st.text_input(
                "Dirección",
                placeholder="Calle Luna 123"
            )
        
        with col2:
            from src.database.rules_loader import RulesDatabase
            rules_db = RulesDatabase()
            project_municipality = st.selectbox(
                "Municipio",
                options=[""] + rules_db.get_municipalities()[:10]
            )
        
        submitted = st.form_submit_button("Crear Proyecto", use_container_width=True, type="primary")
        
        if submitted:
            if all([project_name, project_address, project_municipality]):
                project_id = SessionManager.create_project(
                    name=project_name,
                    address=project_address,
                    municipality=project_municipality
                )
                st.success(f"Proyecto '{project_name}' creado exitosamente")
                st.session_state.show_projects_menu = False
                st.rerun()
            else:
                st.error("Completa todos los campos")


def render_active_projects_list():
    """Lista de proyectos activos"""
    
    st.markdown("### Proyectos Activos")
    
    projects = SessionManager.get_active_projects()
    
    if projects:
        for project in projects[:5]:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{project['name']}**")
                st.caption(f"{project['municipality']}")
            
            with col2:
                if st.button("Abrir", key=f"open_{project['id']}", use_container_width=True):
                    SessionManager.set_current_project(project['id'])
                    st.session_state.show_projects_menu = False
                    st.rerun()
            
            st.divider()
        
        if len(projects) > 5:
            st.info(f"... y {len(projects) - 5} proyectos más")
    else:
        st.info("No hay proyectos activos. Crea uno nuevo")


def render_project_files():
    """Archivos del proyecto actual"""
    
    st.markdown("### Archivos")
    
    current = SessionManager.get_current_project()
    
    if current:
        st.markdown(f"**Proyecto:** {current['name']}")
        
        if current.get('documents'):
            st.markdown("**Documentos:**")
            for doc_type, doc_info in current['documents'].items():
                st.markdown(f"- {doc_type}: `{doc_info['filename']}`")
        else:
            st.info("No hay documentos subidos")
        
        if current.get('reports'):
            st.markdown("**Reportes:**")
            for i, report in enumerate(current['reports']):
                st.download_button(
                    label=f"{report['type']} ({report['generated_date'][:10]})",
                    data=report['data'],
                    file_name=f"{report['type']}_{i}.pdf",
                    mime="application/pdf",
                    key=f"dl_report_{i}"
                )
        else:
            st.info("No hay reportes generados")
    else:
        st.warning("Selecciona un proyecto primero")
        