# Sidebar Navigation Component
import streamlit as st
from src.services.session_manager import SessionManager

def render_sidebar():
    """Renderiza el sidebar de navegación con logo y links"""
    
    SessionManager.initialize()
    
    with st.sidebar:
        # Logo y tagline
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
            <div style="font-size: 2rem; font-weight: 900; 
                        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        letter-spacing: -0.5px;">
                Pyxten
            </div>
            <div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem;">
                Validación Inteligente de Permisos
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Navigation Links
        current_page = SessionManager.get_current_page()
        
        # Homepage / Validación
        if st.button(
            "🏠 Validación Fase 1",
            key="nav_homepage",
            use_container_width=True,
            type="primary" if current_page == "homepage" else "secondary"
        ):
            st.session_state.current_page = 'homepage'
            st.rerun()
        
        # Dashboard
        if st.button(
            "📊 Dashboard",
            key="nav_dashboard",
            use_container_width=True,
            type="primary" if current_page == "dashboard" else "secondary"
        ):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        
        # Crear Nuevo Proyecto
        if st.button(
            "➕ Crear Nuevo Proyecto",
            key="nav_new_project",
            use_container_width=True,
            type="primary" if current_page == "new_project" else "secondary"
        ):
            st.session_state.current_page = 'new_project'
            st.rerun()
        
        # Proyectos Activos
        active_count = len(SessionManager.get_active_projects())
        if st.button(
            f"📁 Proyectos Activos ({active_count})",
            key="nav_active_projects",
            use_container_width=True,
            type="primary" if current_page == "active_projects" else "secondary"
        ):
            st.session_state.current_page = 'active_projects'
            st.rerun()
        
        # Precios
        if st.button(
            "💰 Precios",
            key="nav_pricing",
            use_container_width=True,
            type="primary" if current_page == "pricing" else "secondary"
        ):
            st.session_state.current_page = 'pricing'
            st.rerun()
        
        st.divider()
        
        # Validaciones restantes (mini widget)
        remaining = SessionManager.get_remaining_validations()
        total = st.session_state.validation_limit
        percentage = ((total - remaining) / total) * 100
        
        st.markdown("""
        <div style="padding: 1rem; background: #f9fafb; border-radius: 12px; margin-top: 1rem;">
            <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;">
                Validaciones este mes
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                {used} / {total}
            </div>
            <div style="background: #e5e7eb; border-radius: 8px; height: 6px; overflow: hidden; margin: 0.75rem 0;">
                <div style="background: linear-gradient(90deg, #10b981, #14b8a6); height: 100%; width: {percent}%;"></div>
            </div>
            <div style="font-size: 0.75rem; color: #6b7280;">
                {remaining} validaciones restantes
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
            <div style="padding: 1rem; background: #ecfdf5; border-radius: 12px; margin-top: 1rem; border-left: 3px solid #10b981;">
                <div style="font-size: 0.75rem; color: #059669; font-weight: 600; margin-bottom: 0.25rem;">
                    PROYECTO ACTUAL
                </div>
                <div style="font-size: 0.9rem; font-weight: 600; color: #065f46;">
                    {name}
                </div>
                <div style="font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem;">
                    {municipality}
                </div>
            </div>
            """.format(
                name=current_project['name'],
                municipality=current_project['municipality']
            ), unsafe_allow_html=True)
        
        # Footer del sidebar
        st.markdown("""
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; text-align: center;">
            <div style="font-size: 0.75rem; color: #9ca3af;">
                © 2025 Pyxten LLC<br>
                Desarrollado en 🇵🇷
            </div>
        </div>
        """, unsafe_allow_html=True)