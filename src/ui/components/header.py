# Header Component Mejorado - Navigation Bar Moderno
import streamlit as st
from src.services.session_manager import SessionManager

def render_header():
    """Renderiza el header con navegación moderna estilo SaaS"""
    
    # Inicializar session manager
    SessionManager.initialize()
    
    # CSS Mejorado con diseño moderno
    st.markdown("""
    <style>
        /* Reset default Streamlit padding */
        .main .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            max-width: 100%;
        }
        
        /* Header Principal */
        .pyxten-header {
            background: linear-gradient(135deg, #ffffff 0%, #f8fffe 100%);
            border-bottom: 1px solid #e0e0e0;
            padding: 1rem 3rem;
            margin: -1rem -1rem 2rem -1rem;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        
        /* Logo y Brand */
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .brand-container {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .logo {
            font-size: 2rem;
            font-weight: 900;
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        .tagline {
            font-size: 0.85rem;
            color: #6b7280;
            font-weight: 500;
        }
        
        /* Navigation Bar */
        .nav-bar {
            display: flex;
            gap: 0.5rem;
            align-items: center;
            background: #f9fafb;
            padding: 0.5rem;
            border-radius: 12px;
            width: fit-content;
        }
        
        .nav-item {
            padding: 0.625rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            color: #4b5563;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            background: transparent;
            white-space: nowrap;
        }
        
        .nav-item:hover {
            background: #ffffff;
            color: #10b981;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        .nav-item.active {
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        
        /* Auth Buttons */
        .auth-container {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }
        
        .auth-btn {
            padding: 0.625rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: not-allowed;
            transition: all 0.2s ease;
            opacity: 0.5;
            white-space: nowrap;
        }
        
        .btn-login {
            background: transparent;
            border: 2px solid #10b981;
            color: #10b981;
        }
        
        .btn-signup {
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            border: none;
            color: white;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
        }
        
        .phase-badge {
            font-size: 0.7rem;
            background: #fef3c7;
            color: #92400e;
            padding: 0.15rem 0.5rem;
            border-radius: 12px;
            font-weight: 700;
            margin-left: 0.5rem;
        }
        
        /* Dropdown Menu Moderno */
        .dropdown-menu {
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            padding: 0.5rem;
            margin-top: 0.5rem;
            min-width: 280px;
        }
        
        .dropdown-item {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .dropdown-item:hover {
            background: #f3f4f6;
        }
        
        .dropdown-icon {
            font-size: 1.25rem;
        }
        
        /* Project Counter Badge */
        .counter-badge {
            background: #10b981;
            color: white;
            padding: 0.15rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-left: auto;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .pyxten-header {
                padding: 1rem;
            }
            
            .header-top {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
            
            .nav-bar {
                width: 100%;
                overflow-x: auto;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header HTML
    st.markdown("""
    <div class="pyxten-header">
        <div class="header-top">
            <div class="brand-container">
                <div class="logo">Py✗ten</div>
                <div class="tagline">Validación Inteligente de Permisos en Puerto Rico</div>
            </div>
            
            <div class="auth-container">
                <div class="auth-btn btn-login">
                    Iniciar Sesión
                    <span class="phase-badge">FASE 3</span>
                </div>
                <div class="auth-btn btn-signup">
                    Regístrate
                    <span class="phase-badge">FASE 3</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation usando columns para mejor control
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 2])
    
    current_page = SessionManager.get_current_page()
    
    with nav_col1:
        if st.button("🏠 Dashboard", key="nav_dashboard", 
                    type="primary" if current_page == "dashboard" else "secondary",
                    use_container_width=True):
            SessionManager.navigate_to('dashboard')
    
    with nav_col2:
        if st.button("📁 Proyectos", key="nav_projects",
                    type="primary" if current_page == "projects" else "secondary",
                    use_container_width=True):
            # Toggle projects menu
            if 'show_projects_menu' not in st.session_state:
                st.session_state.show_projects_menu = False
            st.session_state.show_projects_menu = not st.session_state.show_projects_menu
    
    with nav_col3:
        if st.button("💳 Precios", key="nav_pricing",
                    type="primary" if current_page == "pricing" else "secondary",
                    use_container_width=True):
            SessionManager.navigate_to('pricing')
    
    with nav_col4:
        if st.button("⚙️ Config", key="nav_settings",
                    disabled=True,
                    use_container_width=True):
            st.toast("⚙️ Configuraciones estará disponible en Phase 3")
    
    with nav_col5:
        if st.button("📚 Ayuda", key="nav_help",
                    use_container_width=True):
            st.session_state.show_help = True
    
    # Dropdown de Proyectos
    if st.session_state.get('show_projects_menu', False):
        render_projects_dropdown()
    
    # Modal de Ayuda
    if st.session_state.get('show_help', False):
        render_help_modal()
    
    st.divider()


def render_projects_dropdown():
    """Renderiza el menú dropdown de proyectos"""
    
    with st.expander("📁 Gestión de Proyectos", expanded=True):
        tab1, tab2, tab3 = st.tabs(["➕ Nuevo", "📂 Activos", "📄 Archivos"])
        
        with tab1:
            render_new_project_form()
        
        with tab2:
            render_active_projects_list()
        
        with tab3:
            render_project_files()


def render_new_project_form():
    """Formulario para crear nuevo proyecto"""
    
    st.markdown("### 🆕 Crear Nuevo Proyecto")
    
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
                options=[""] + rules_db.get_municipalities()[:10]  # Top 10 para dropdown
            )
        
        submitted = st.form_submit_button("✅ Crear Proyecto", use_container_width=True, type="primary")
        
        if submitted:
            if all([project_name, project_address, project_municipality]):
                project_id = SessionManager.create_project(
                    name=project_name,
                    address=project_address,
                    municipality=project_municipality
                )
                st.success(f"✅ Proyecto '{project_name}' creado!")
                st.session_state.show_projects_menu = False
                st.rerun()
            else:
                st.error("⚠️ Completa todos los campos")


def render_active_projects_list():
    """Lista de proyectos activos"""
    
    st.markdown("### 📂 Proyectos Activos")
    
    projects = SessionManager.get_active_projects()
    
    if projects:
        for project in projects[:5]:  # Mostrar solo primeros 5
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{project['name']}**")
                st.caption(f"📍 {project['municipality']}")
            
            with col2:
                if st.button("Abrir", key=f"open_{project['id']}", use_container_width=True):
                    SessionManager.set_current_project(project['id'])
                    st.session_state.show_projects_menu = False
                    st.rerun()
            
            st.divider()
        
        if len(projects) > 5:
            st.info(f"... y {len(projects) - 5} proyectos más")
    else:
        st.info("No hay proyectos activos. ¡Crea uno nuevo!")


def render_project_files():
    """Archivos del proyecto actual"""
    
    st.markdown("### 📄 Archivos")
    
    current = SessionManager.get_current_project()
    
    if current:
        st.markdown(f"**Proyecto:** {current['name']}")
        
        # Documentos
        if current.get('documents'):
            st.markdown("**📎 Documentos:**")
            for doc_type, doc_info in current['documents'].items():
                st.markdown(f"- ✓ {doc_type}: `{doc_info['filename']}`")
        else:
            st.info("No hay documentos subidos")
        
        # Reportes
        if current.get('reports'):
            st.markdown("**📄 Reportes:**")
            for i, report in enumerate(current['reports']):
                st.download_button(
                    label=f"📥 {report['type']} ({report['generated_date'][:10]})",
                    data=report['data'],
                    file_name=f"{report['type']}_{i}.pdf",
                    mime="application/pdf",
                    key=f"dl_report_{i}"
                )
        else:
            st.info("No hay reportes generados")
    else:
        st.warning("Selecciona un proyecto primero")


def render_help_modal():
    """Modal de ayuda"""
    
    with st.expander("📚 Centro de Ayuda", expanded=True):
        st.markdown("""
        ### ¿Cómo usar Pyxten?
        
        **Fase 1 - Validación de Zonificación:**
        1. 🏠 Ingresa la dirección de tu propiedad
        2. 📍 Selecciona municipio y zonificación
        3. 🏗️ Indica el uso propuesto
        4. 🔍 Presiona "Validar Proyecto"
        5. 📄 Descarga tu reporte en PDF
        
        **Recursos Útiles:**
        - 📖 [Documentación Completa](https://pyxten.com/docs)
        - 📹 [Video Tutoriales](https://youtube.com/@pyxten)
        - 💬 [Chat en Vivo](mailto:soporte@pyxten.com)
        - 📞 Teléfono: (787) 506-0402
        
        **Próximamente en Fase 2:**
        - ✓ Validación completa de PCOC
        - ✓ Análisis de documentos con IA
        - ✓ Memorial Explicativo automático
        """)
        
        if st.button("Cerrar Ayuda", use_container_width=True):
            st.session_state.show_help = False
            st.rerun()