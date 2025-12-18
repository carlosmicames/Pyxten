# Dashboard Component - FINAL: Sin emojis, con botón Comienza ahora
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
    
    # 4 Cards en 2 filas
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    # Card 1: Validaciones Recientes
    with row1_col1:
        render_recent_validations_card()
    
    # Card 2: Proyectos Activos
    with row1_col2:
        render_active_projects_card()
    
    # Card 3: Nueva Validación
    with row2_col1:
        render_new_validation_card()
    
    # Card 4: Uso del Mes
    with row2_col2:
        render_usage_card()


def render_recent_validations_card():
    """Card de validaciones recientes"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Validaciones Recientes")
    
    history = SessionManager.get_validation_history()
    
    if history:
        for val in history[:5]:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{val.get('property_address', 'Sin dirección')}**")
                    st.caption(f"{val.get('municipality', '')} | {val.get('timestamp', '')[:10]}")
                
                with col2:
                    if val.get('viable'):
                        st.markdown("Viable")
                    else:
                        st.markdown("No Viable")
                
                st.divider()
    else:
        st.info("No hay validaciones recientes. Crea tu primera validación")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_active_projects_card():
    """Card de proyectos activos"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Proyectos Activos")
    
    projects = SessionManager.get_active_projects()
    
    if projects:
        st.markdown(f'<div class="card-value">{len(projects)}</div>', unsafe_allow_html=True)
        st.caption(f"proyecto{'s' if len(projects) != 1 else ''} en progreso")
        
        st.divider()
        
        for project in projects[:3]:
            with st.container():
                st.markdown(f"**{project['name']}**")
                st.caption(f"Creado: {project['created_date'][:10]}")
                
                if st.button("Ver Detalles", key=f"view_{project['id']}", use_container_width=True):
                    SessionManager.set_current_project(project['id'])
                    st.rerun()
                
                st.divider()
    else:
        st.info("No tienes proyectos activos")
        if st.button("Crear Proyecto", key="create_new_proj", use_container_width=True):
            st.info("Usa el menú 'Proyectos' para crear uno")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_new_validation_card():
    """Card de nueva validación - CTA principal con botón Comienza ahora"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### Nueva Validación")
    
    can_validate = SessionManager.can_validate()
    
    if can_validate:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <p style="font-size: 1.1rem; color: #374151;">
                ¿Listo para comenzar tu proyecto?
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón "Comienza ahora" que navega a Proyectos
        if st.button(
            "Comienza ahora",
            key="start_project_now",
            type="primary",
            use_container_width=True
        ):
            st.session_state.current_page = 'projects'
            st.session_state.show_projects_menu = True
            st.rerun()
    else:
        st.warning("""
        Has alcanzado el límite de validaciones gratuitas este mes.
        
        **Actualiza a Plan Profesional para:**
        - Validaciones ilimitadas Fase 1
        - 10 validaciones PCOC/mes
        - Memorial Explicativo generado
        - Proyectos guardados
        """)
        
        if st.button("Ver Planes", key="upgrade_plan", use_container_width=True):
            st.session_state.current_page = 'pricing'
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