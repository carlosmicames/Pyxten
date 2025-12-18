# Header Component - Menú de navegación superior
import streamlit as st
from src.services.session_manager import SessionManager

def render_header():
    """Renderiza el header con navegación y logo"""
    
    # Inicializar session manager
    SessionManager.initialize()
    
    st.markdown("""
    <style>
        /* Header Container */
        .header-container {
            background: white;
            padding: 1rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        /* Logo */
        .logo {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }
        
        /* Navigation */
        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
        }
        
        .nav-left {
            display: flex;
            gap: 2rem;
            align-items: center;
        }
        
        .nav-right {
            display: flex;
            gap: 1rem;
        }
        
        .nav-item {
            color: #374151;
            text-decoration: none;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .nav-item:hover {
            background: #f3f4f6;
            color: #10b981;
        }
        
        .nav-item.active {
            background: #ecfdf5;
            color: #10b981;
        }
        
        /* Auth Buttons */
        .auth-button {
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: not-allowed;
            opacity: 0.5;
        }
        
        .btn-login {
            background: white;
            border: 2px solid #10b981;
            color: #10b981;
        }
        
        .btn-signup {
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            border: none;
            color: white;
        }
        
        /* Dropdown */
        .dropdown {
            position: relative;
            display: inline-block;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header HTML
    st.markdown("""
    <div class="header-container">
        <div class="logo">Py✗ten</div>
        <div style="font-size: 0.9rem; color: #6b7280; margin-top: 0.25rem;">
            Validación Inteligente de Permisos en Puerto Rico
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation Bar
    col_nav, col_auth = st.columns([3, 1])
    
    with col_nav:
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 Dashboard", 
            "📁 Proyectos", 
            "💳 Precios",
            "⚙️ Configuraciones",
            "📚 Ayuda"
        ])
        
        with tab1:
            if SessionManager.get_current_page() != 'dashboard':
                SessionManager.navigate_to('dashboard')
        
        with tab2:
            render_projects_dropdown()
        
        with tab3:
            if SessionManager.get_current_page() != 'pricing':
                SessionManager.navigate_to('pricing')
        
        with tab4:
            st.info("⚙️ Configuraciones estará disponible en Phase 3")
        
        with tab5:
            st.info("""
            📚 **Recursos de Ayuda**
            
            - 📖 [Documentación](https://pyxten.com/docs)
            - 💬 [Soporte](mailto:soporte@pyxten.com)
            - 📞 Teléfono: (787) 506-0402
            """)
    
    with col_auth:
        st.markdown('<div style="text-align: right;">', unsafe_allow_html=True)
        
        col_login, col_signup = st.columns(2)
        
        with col_login:
            if st.button("Iniciar Sesión", disabled=True, use_container_width=True):
                pass
            st.caption("_Fase 3_")
        
        with col_signup:
            if st.button("Regístrate", disabled=True, type="primary", use_container_width=True):
                pass
            st.caption("_Fase 3_")
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_projects_dropdown():
    """Renderiza el dropdown de proyectos"""
    
    st.markdown("### 📁 Gestión de Proyectos")
    
    # Opciones del dropdown
    option = st.radio(
        "Selecciona una opción:",
        ["🆕 Proyecto Nuevo", "📂 Proyectos Activos", "📄 Mis Archivos"],
        label_visibility="collapsed"
    )
    
    if option == "🆕 Proyecto Nuevo":
        st.markdown("#### Crear Nuevo Proyecto")
        
        with st.form("new_project_form"):
            project_name = st.text_input(
                "Nombre del Proyecto",
                placeholder="Ej: Residencia Familia García"
            )
            
            project_address = st.text_input(
                "Dirección",
                placeholder="Ej: Calle Luna 123, Urb. San Patricio"
            )
            
            project_municipality = st.selectbox(
                "Municipio",
                ["Seleccionar..."] + ["San Juan", "Guaynabo", "Bayamón", "Carolina"]
            )
            
            submitted = st.form_submit_button("✅ Crear Proyecto", type="primary")
            
            if submitted:
                if project_name and project_address and project_municipality != "Seleccionar...":
                    project_id = SessionManager.create_project(
                        name=project_name,
                        address=project_address,
                        municipality=project_municipality
                    )
                    st.success(f"✅ Proyecto '{project_name}' creado exitosamente!")
                    st.info(f"ID del Proyecto: `{project_id}`")
                    SessionManager.navigate_to('dashboard')
                else:
                    st.error("Por favor completa todos los campos")
    
    elif option == "📂 Proyectos Activos":
        st.markdown("#### Proyectos Activos")
        
        projects = SessionManager.get_active_projects()
        
        if projects:
            for project in projects:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{project['name']}**")
                        st.caption(f"{project['address']} | {project['municipality']}")
                    
                    with col2:
                        status_color = "🟢" if project['status'] == "En Progreso" else "🔵"
                        st.markdown(f"{status_color} {project['status']}")
                    
                    with col3:
                        if st.button("Abrir", key=f"open_{project['id']}", use_container_width=True):
                            SessionManager.set_current_project(project['id'])
                            SessionManager.navigate_to('dashboard')
                    
                    st.divider()
        else:
            st.info("No tienes proyectos activos. Crea uno nuevo para empezar.")
    
    elif option == "📄 Mis Archivos":
        st.markdown("#### Mis Archivos")
        
        current_project = SessionManager.get_current_project()
        
        if current_project:
            st.markdown(f"**Proyecto:** {current_project['name']}")
            
            # Mostrar documentos
            if current_project.get('documents'):
                st.markdown("**📎 Documentos Subidos:**")
                for doc_type, doc_info in current_project['documents'].items():
                    st.markdown(f"- {doc_type}: `{doc_info['filename']}`")
            else:
                st.info("No hay documentos en este proyecto aún.")
            
            # Mostrar reportes
            if current_project.get('reports'):
                st.markdown("**📄 Reportes Generados:**")
                for i, report in enumerate(current_project['reports']):
                    st.download_button(
                        label=f"📥 {report['type']} - {report['generated_date'][:10]}",
                        data=report['data'],
                        file_name=f"reporte_{report['type']}_{i}.pdf",
                        mime="application/pdf",
                        key=f"download_report_{i}"
                    )
            else:
                st.info("No hay reportes generados aún.")
        else:
            st.warning("Selecciona o crea un proyecto primero.")