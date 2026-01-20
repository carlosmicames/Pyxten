# Dashboard Component - CORRECTED with all fixes
import streamlit as st
from src.services.session_manager import SessionManager
from datetime import datetime

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
    
    # Header del dashboard
    current_project = SessionManager.get_current_project()
    
    if current_project:
        st.markdown(f"## {current_project['name']}")
        st.caption(f"{current_project['address']} | {current_project['municipality']}")
    else:
        st.markdown("## Dashboard")
        st.caption("Panel de control de Pyxten")
    
    st.divider()
    
    # FIXED: New layout structure
    # Row 1: Validaciones Recientes (full width)
    render_recent_validations_card()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 2: Nueva Validación and Mis Proyectos in same row
    col1, col2 = st.columns(2)
    
    with col1:
        render_nueva_validacion_button()
    
    with col2:
        render_mis_proyectos_button()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Row 3: Uso del Mes (full width below)
    render_usage_card()


def render_recent_validations_card():
    """Card de validaciones recientes con descripción y PDF download"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Validaciones Recientes")
    
    history = SessionManager.get_validation_history()
    
    if history:
        for i, val in enumerate(history[:5]):
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 1])
                
                with col1:
                    st.markdown(f"**{val.get('property_address', 'Sin dirección')}**")
                    
                    # Show project description
                    description = val.get('project_description', val.get('description', ''))
                    if description:
                        st.caption(f"📝 {description[:50]}{'...' if len(description) > 50 else ''}")
                    
                    st.caption(f"📍 {val.get('municipality', '')} | 📅 {val.get('timestamp', '')[:10]}")
                
                with col2:
                    if val.get('viable'):
                        st.success("✅ Viable")
                    else:
                        st.error("❌ No Viable")
                
                with col3:
                    # PDF Download button
                    pdf_data = val.get('pdf_data')
                    if pdf_data:
                        st.download_button(
                            label="📥",
                            data=pdf_data,
                            file_name=f"reporte_{i+1}.pdf",
                            mime="application/pdf",
                            key=f"download_recent_{i}",
                            help="Descargar PDF"
                        )
                    else:
                        st.button(
                            "📥",
                            disabled=True,
                            key=f"no_pdf_{i}",
                            help="Reporte no disponible"
                        )
                
                if i < len(history[:5]) - 1:
                    st.divider()
    else:
        st.info("📋 No hay validaciones recientes. Crea tu primera validación!")
        
        if st.button("➕ Nueva Validación", key="new_val_from_empty", use_container_width=True):
            st.session_state.current_page = 'homepage'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_nueva_validacion_button():
    """Simple card with Nueva Validación button"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    can_validate = SessionManager.can_validate()
    
    if can_validate:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #374151; margin-bottom: 1rem;">
                Nueva Validación
            </div>
            <div style="color: #6b7280; margin-bottom: 1.5rem;">
                Valida tu proyecto de construcción
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(
            "Comenzar Validación",
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
                Límite Alcanzado
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("Has alcanzado el límite de validaciones gratuitas este mes.")
        
        if st.button("Ver Planes", key="upgrade_from_nueva_val", use_container_width=True):
            st.session_state.current_page = 'pricing'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_mis_proyectos_button():
    """Simple card with Mis Proyectos button"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    projects = SessionManager.get_all_projects()
    project_count = len(projects)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <div style="font-size: 1.5rem; font-weight: 700; color: #374151; margin-bottom: 1rem;">
            Mis Proyectos
        </div>
        <div style="font-size: 2.5rem; font-weight: 800; color: #10b981; margin-bottom: 0.5rem;">
            {project_count}
        </div>
        <div style="color: #6b7280; margin-bottom: 1.5rem;">
            proyecto{'s' if project_count != 1 else ''} guardado{'s' if project_count != 1 else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(
        "Ver Proyectos",
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
    percentage = (used / limit) * 100
    
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="stat-item">
            <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                {count}
            </div>
            <div style="font-size: 0.85rem; color: #6b7280;">
                Proyectos
            </div>
        </div>
        """.format(count=len(SessionManager.get_all_projects())), unsafe_allow_html=True)
    
    with col2:
        viable_count = sum(1 for v in SessionManager.get_validation_history() if v.get('viable'))
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