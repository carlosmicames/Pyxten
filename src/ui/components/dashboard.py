# Dashboard Component Mejorado - Diseño Moderno tipo SaaS
import streamlit as st
from src.services.session_manager import SessionManager
from datetime import datetime

def render_dashboard():
    """Renderiza el dashboard principal con diseño moderno"""
    
    SessionManager.initialize()
    
    # CSS Mejorado con animaciones y diseño moderno
    st.markdown("""
    <style>
        /* Dashboard Container */
        .dashboard-container {
            padding: 1rem 0;
        }
        
        /* Welcome Section */
        .welcome-section {
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            padding: 2.5rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25);
            position: relative;
            overflow: hidden;
        }
        
        .welcome-section::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 300px;
            height: 300px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
        }
        
        .welcome-title {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 1;
        }
        
        .welcome-subtitle {
            font-size: 1.1rem;
            opacity: 0.95;
            position: relative;
            z-index: 1;
        }
        
        /* Cards Grid */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        /* Dashboard Cards Modernos */
        .dashboard-card {
            background: white;
            padding: 1.75rem;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid #f0f0f0;
            position: relative;
            overflow: hidden;
        }
        
        .dashboard-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #10b981 0%, #14b8a6 100%);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }
        
        .dashboard-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
        }
        
        .dashboard-card:hover::before {
            transform: scaleX(1);
        }
        
        /* Card Header */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .card-icon {
            font-size: 2.5rem;
            opacity: 0.9;
        }
        
        .card-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #374151;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Card Content */
        .card-value {
            font-size: 2.75rem;
            font-weight: 900;
            color: #10b981;
            margin: 0.75rem 0;
            line-height: 1;
        }
        
        .card-label {
            font-size: 0.9rem;
            color: #6b7280;
            font-weight: 500;
        }
        
        /* Progress Bar Mejorado */
        .progress-wrapper {
            margin: 1rem 0;
        }
        
        .progress-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }
        
        .progress-container {
            background: #f3f4f6;
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-bar {
            background: linear-gradient(90deg, #10b981, #14b8a6);
            height: 100%;
            border-radius: 10px;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .progress-bar::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3),
                transparent
            );
            animation: shimmer 2s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        /* List Items */
        .list-item {
            padding: 0.875rem;
            background: #f9fafb;
            border-radius: 10px;
            margin: 0.5rem 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }
        
        .list-item:hover {
            background: #f3f4f6;
            border-color: #e5e7eb;
            transform: translateX(2px);
        }
        
        .list-item-title {
            font-weight: 600;
            color: #374151;
            font-size: 0.95rem;
        }
        
        .list-item-subtitle {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 0.15rem;
        }
        
        /* Status Badge */
        .status-badge {
            padding: 0.35rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            white-space: nowrap;
        }
        
        .status-viable {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-not-viable {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .status-progress {
            background: #fef3c7;
            color: #92400e;
        }
        
        /* CTA Card */
        .cta-card {
            background: linear-gradient(135deg, #f0fdf4 0%, #d1fae5 100%);
            border: 2px solid #10b981;
        }
        
        .cta-content {
            text-align: center;
            padding: 1rem 0;
        }
        
        .cta-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .cta-text {
            font-size: 1.15rem;
            color: #065f46;
            font-weight: 600;
            margin-bottom: 1.5rem;
        }
        
        /* Stats Mini Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            margin-top: 1rem;
        }
        
        .stat-mini-card {
            background: #f9fafb;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #e5e7eb;
        }
        
        .stat-mini-value {
            font-size: 1.75rem;
            font-weight: 800;
            color: #10b981;
            line-height: 1;
        }
        
        .stat-mini-label {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 0.35rem;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 2rem 1rem;
            color: #9ca3af;
        }
        
        .empty-state-icon {
            font-size: 3rem;
            opacity: 0.5;
            margin-bottom: 0.5rem;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .dashboard-card {
            animation: fadeIn 0.5s ease backwards;
        }
        
        .dashboard-card:nth-child(1) { animation-delay: 0.1s; }
        .dashboard-card:nth-child(2) { animation-delay: 0.2s; }
        .dashboard-card:nth-child(3) { animation-delay: 0.3s; }
        .dashboard-card:nth-child(4) { animation-delay: 0.4s; }
    </style>
    """, unsafe_allow_html=True)
    
    # Welcome Section
    current_project = SessionManager.get_current_project()
    
    if current_project:
        st.markdown(f"""
        <div class="welcome-section">
            <div class="welcome-title">📁 {current_project['name']}</div>
            <div class="welcome-subtitle">
                📍 {current_project['address']} | {current_project['municipality']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="welcome-section">
            <div class="welcome-title">👋 Bienvenido a Pyxten</div>
            <div class="welcome-subtitle">
                Valida tus proyectos de construcción en minutos, no en meses
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 4 Cards en Grid
    col1, col2 = st.columns(2)
    
    with col1:
        render_recent_validations_card()
        render_new_validation_card()
    
    with col2:
        render_active_projects_card()
        render_usage_card()


def render_recent_validations_card():
    """Card 1: Validaciones Recientes"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card-header">
        <div>
            <div class="card-icon">📋</div>
            <div class="card-title">Validaciones Recientes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    history = SessionManager.get_validation_history()
    
    if history:
        for val in history[:5]:
            viable = val.get('viable', False)
            status_class = 'status-viable' if viable else 'status-not-viable'
            status_text = '✓ Viable' if viable else '✗ No Viable'
            
            st.markdown(f"""
            <div class="list-item">
                <div>
                    <div class="list-item-title">{val.get('property_address', 'Sin dirección')[:30]}...</div>
                    <div class="list-item-subtitle">
                        {val.get('municipality', '')} | {val.get('timestamp', '')[:10]}
                    </div>
                </div>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <div>No hay validaciones recientes</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem;">
                ¡Crea tu primera validación abajo!
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_active_projects_card():
    """Card 2: Proyectos Activos"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card-header">
        <div>
            <div class="card-icon">📂</div>
            <div class="card-title">Proyectos Activos</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    projects = SessionManager.get_active_projects()
    
    if projects:
        st.markdown(f"""
        <div class="card-value">{len(projects)}</div>
        <div class="card-label">proyecto{'s' if len(projects) != 1 else ''} en progreso</div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        for project in projects[:3]:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="list-item">
                    <div>
                        <div class="list-item-title">{project['name'][:25]}</div>
                        <div class="list-item-subtitle">
                            Creado: {project['created_date'][:10]}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("→", key=f"view_{project['id']}", help="Ver detalles"):
                    SessionManager.set_current_project(project['id'])
                    st.rerun()
        
        if len(projects) > 3:
            st.info(f"+ {len(projects) - 3} proyectos más")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div>No hay proyectos activos</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ Crear Primer Proyecto", key="create_first", use_container_width=True, type="primary"):
            st.info("💡 Usa el menú 'Proyectos' → 'Nuevo' en el header")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_new_validation_card():
    """Card 3: Nueva Validación (CTA Principal)"""
    
    st.markdown('<div class="dashboard-card cta-card">', unsafe_allow_html=True)
    
    can_validate = SessionManager.can_validate()
    
    if can_validate:
        st.markdown("""
        <div class="cta-content">
            <div class="cta-icon">🚀</div>
            <div class="cta-text">¿Listo para validar tu proyecto?</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(
            "🔍 Iniciar Validación Fase 1",
            key="start_validation_cta",
            type="primary",
            use_container_width=True
        ):
            # Scroll automático al formulario (será implementado con st.query_params)
            st.info("👇 Completa el formulario abajo para comenzar")
            st.session_state.scroll_to_form = True
    else:
        st.markdown("""
        <div class="cta-content">
            <div class="cta-icon">🔒</div>
            <div class="cta-text" style="color: #dc2626;">Límite Alcanzado</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("Has usado todas tus validaciones gratuitas este mes.")
        
        st.markdown("""
        **Actualiza a Plan Profesional:**
        - ✅ Validaciones ilimitadas
        - ✅ PCOC con IA
        - ✅ Memorial automático
        """)
        
        if st.button("💳 Ver Planes", key="upgrade_cta", use_container_width=True):
            SessionManager.navigate_to('pricing')
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_usage_card():
    """Card 4: Uso Mensual"""
    
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card-header">
        <div>
            <div class="card-icon">📊</div>
            <div class="card-title">Uso del Mes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    used = st.session_state.validation_count
    limit = st.session_state.validation_limit
    remaining = SessionManager.get_remaining_validations()
    percentage = (used / limit) * 100 if limit > 0 else 0
    
    # Progress bar
    st.markdown(f"""
    <div class="progress-wrapper">
        <div class="progress-label">
            <span><strong>{used}</strong> de <strong>{limit}</strong> utilizadas</span>
            <span>{percentage:.0f}%</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {percentage}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if remaining > 0:
        st.success(f"✅ **{remaining}** validaciones restantes")
    else:
        st.error("❌ Sin validaciones restantes")
    
    # Mini stats
    st.markdown("<br>", unsafe_allow_html=True)
    
    viable_count = sum(1 for v in SessionManager.get_validation_history() if v.get('viable'))
    total_projects = len(SessionManager.get_all_projects())
    
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-mini-card">
            <div class="stat-mini-value">{total_projects}</div>
            <div class="stat-mini-label">Proyectos</div>
        </div>
        <div class="stat-mini-card">
            <div class="stat-mini-value">{viable_count}</div>
            <div class="stat-mini-label">Viables</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)