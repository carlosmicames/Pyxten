# Sidebar Navigation Component - Clean, minimal styling
import streamlit as st
from src.services.session_manager import SessionManager

def render_sidebar():
    """Renderiza el sidebar de navegacion con estilo profesional minimalista"""
    
    SessionManager.initialize()
    
    with st.sidebar:
        # Logo con gradiente - mantenido
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0 1.5rem 0;">
            <div style="font-size: 1.8rem; font-weight: 900; 
                        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        letter-spacing: -0.5px;">
                Pyxten
            </div>
            <div style="font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem;">
                Validacion Inteligente de Permisos
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 0 0 0.75rem 0; border: none; border-top: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
        
        # Custom CSS for compact navigation
        st.markdown("""
        <style>
            /* Compact sidebar buttons */
            [data-testid="stSidebar"] .stButton > button {
                margin-bottom: 0.25rem !important;
                padding: 0.5rem 0.75rem !important;
                font-size: 0.9rem !important;
                border-radius: 6px !important;
                border: none !important;
                background: transparent !important;
                color: #374151 !important;
                text-align: left !important;
                justify-content: flex-start !important;
            }
            
            [data-testid="stSidebar"] .stButton > button:hover {
                background: #f3f4f6 !important;
            }
            
            [data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: #ecfdf5 !important;
                color: #059669 !important;
                font-weight: 600 !important;
            }
            
            /* Remove default padding from sidebar elements */
            [data-testid="stSidebar"] > div:first-child {
                padding-top: 0 !important;
            }
            
            /* Compact vertical rhythm */
            [data-testid="stSidebar"] .element-container {
                margin-bottom: 0 !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Navigation Links - sin emojis, texto limpio
        current_page = SessionManager.get_current_page()
        
        # Validacion Fase 1
        if st.button(
            "Validacion Fase 1",
            key="nav_homepage",
            use_container_width=True,
            type="primary" if current_page == "homepage" else "secondary"
        ):
            st.session_state.current_page = 'homepage'
            st.rerun()
        
        # Dashboard
        if st.button(
            "Dashboard",
            key="nav_dashboard",
            use_container_width=True,
            type="primary" if current_page == "dashboard" else "secondary"
        ):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        
        # Crear Nuevo Proyecto
        if st.button(
            "Crear Nuevo Proyecto",
            key="nav_new_project",
            use_container_width=True,
            type="primary" if current_page == "new_project" else "secondary"
        ):
            st.session_state.current_page = 'new_project'
            st.rerun()
        
        # Proyectos Activos
        active_count = len(SessionManager.get_active_projects())
        if st.button(
            f"Proyectos Activos ({active_count})",
            key="nav_active_projects",
            use_container_width=True,
            type="primary" if current_page == "active_projects" else "secondary"
        ):
            st.session_state.current_page = 'active_projects'
            st.rerun()
        
        # Precios
        if st.button(
            "Precios",
            key="nav_pricing",
            use_container_width=True,
            type="primary" if current_page == "pricing" else "secondary"
        ):
            st.session_state.current_page = 'pricing'
            st.rerun()
        
        st.markdown("<hr style='margin: 0.75rem 0; border: none; border-top: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
        
        # Validaciones restantes - widget compacto
        remaining = SessionManager.get_remaining_validations()
        total = st.session_state.validation_limit
        percentage = ((total - remaining) / total) * 100
        
        st.markdown("""
        <div style="padding: 0.75rem; background: #f9fafb; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 0.25rem;">
                Validaciones este mes
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #10b981;">
                {used} / {total}
            </div>
            <div style="background: #e5e7eb; border-radius: 4px; height: 4px; overflow: hidden; margin: 0.5rem 0;">
                <div style="background: linear-gradient(90deg, #10b981, #14b8a6); height: 100%; width: {percent}%;"></div>
            </div>
            <div style="font-size: 0.7rem; color: #9ca3af;">
                {remaining} restantes
            </div>
        </div>
        """.format(
            used=total - remaining,
            total=total,
            percent=percentage,
            remaining=remaining
        ), unsafe_allow_html=True)
        
        # Proyecto actual (si existe)
        current_project = SessionManager.get_current_project()
        if current_project:
            st.markdown("""
            <div style="padding: 0.75rem; background: #ecfdf5; border-radius: 8px; margin-top: 0.5rem; border-left: 3px solid #10b981;">
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Proyecto Actual
                </div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #065f46; margin-top: 0.25rem;">
                    {name}
                </div>
                <div style="font-size: 0.7rem; color: #6b7280;">
                    {municipality}
                </div>
            </div>
            """.format(
                name=current_project['name'],
                municipality=current_project['municipality']
            ), unsafe_allow_html=True)
        
        # Footer del sidebar - compacto
        st.markdown("""
        <div style="margin-top: 1.5rem; padding-top: 0.75rem; border-top: 1px solid #e5e7eb; text-align: center;">
            <div style="font-size: 0.65rem; color: #9ca3af;">
                2025 Pyxten LLC | Puerto Rico
            </div>
        </div>
        """, unsafe_allow_html=True)