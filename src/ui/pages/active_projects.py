# Página de proyectos activos
import streamlit as st
from src.services.session_manager import SessionManager
import json

def render_active_projects_page():
    """Página dedicada para ver y gestionar proyectos activos"""
    
    SessionManager.initialize()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827;">
            📁 Proyectos Activos
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Gestiona y monitorea todos tus proyectos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    projects = SessionManager.get_all_projects()
    
    if not projects:
        # Empty state
        st.markdown("""
        <div style="background: white; padding: 3rem; border-radius: 16px; 
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); text-align: center;
                    max-width: 600px; margin: 2rem auto;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📂</div>
            <h2 style="color: #374151; margin-bottom: 1rem;">
                No tienes proyectos todavía
            </h2>
            <p style="color: #6b7280; font-size: 1.1rem; margin-bottom: 2rem;">
                Crea tu primer proyecto para empezar a organizar tus validaciones
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ Crear Mi Primer Proyecto", type="primary", use_container_width=True):
                st.session_state.current_page = 'new_project'
                st.rerun()
        
        return
    
    # Stats bar
    active_projects = [p for p in projects.values() if p['status'] == 'En Progreso']
    completed_projects = [p for p in projects.values() if p['status'] == 'Completado']
    
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
            options=["Más reciente", "Más antiguo", "Nombre A-Z", "Nombre Z-A"]
        )
    
    with col3:
        if st.button("➕ Nuevo Proyecto", use_container_width=True):
            st.session_state.current_page = 'new_project'
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filter projects
    filtered_projects = list(projects.values())
    
    if filter_status != "Todos":
        filtered_projects = [p for p in filtered_projects if p['status'] == filter_status]
    
    # Sort projects
    if sort_by == "Más reciente":
        filtered_projects.sort(key=lambda p: p['created_date'], reverse=True)
    elif sort_by == "Más antiguo":
        filtered_projects.sort(key=lambda p: p['created_date'])
    elif sort_by == "Nombre A-Z":
        filtered_projects.sort(key=lambda p: p['name'])
    elif sort_by == "Nombre Z-A":
        filtered_projects.sort(key=lambda p: p['name'], reverse=True)
    
    # Display projects
    if not filtered_projects:
        st.info(f"No hay proyectos con estado '{filter_status}'")
    else:
        for project in filtered_projects:
            render_project_card(project)


def render_project_card(project):
    """Renderiza una tarjeta de proyecto con acciones"""
    
    # Status badge color
    status_colors = {
        'En Progreso': ('#f59e0b', '#fef3c7'),
        'Completado': ('#10b981', '#d1fae5'),
        'Pausado': ('#ef4444', '#fee2e2')
    }
    
    badge_color, bg_color = status_colors.get(project['status'], ('#6b7280', '#f3f4f6'))
    
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
                {project['status']}
            </span>
        </div>
        <h3 style="margin: 0.5rem 0; color: #111827; font-size: 1.3rem;">
            {project['name']}
        </h3>
        <p style="color: #6b7280; margin: 0.25rem 0; font-size: 0.9rem;">
            📍 {project['address']}
        </p>
        <p style="color: #9ca3af; margin: 0.25rem 0; font-size: 0.85rem;">
            🏛️ {project['municipality']}
        </p>
        """, unsafe_allow_html=True)
    
    with col2:
        # Project progress
        phase1_icon = "✅" if project.get('phase1_completed') else "⭕"
        docs_count = len(project.get('documents', {}))
        reports_count = len(project.get('reports', []))
        
        st.markdown(f"""
        <div style="font-size: 0.9rem; color: #6b7280;">
            {phase1_icon} <strong>Fase 1:</strong> {'Completa' if project.get('phase1_completed') else 'Pendiente'}<br>
            📄 <strong>Documentos:</strong> {docs_count}<br>
            📊 <strong>Reportes:</strong> {reports_count}<br>
            📅 <strong>Creado:</strong> {project['created_date'][:10]}
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Actions
        if st.button("👁️ Ver Detalles", key=f"view_{project['id']}", use_container_width=True):
            SessionManager.set_current_project(project['id'])
            st.success(f"Proyecto '{project['name']}' seleccionado")
            st.rerun()
        
        if st.button("📝 Editar", key=f"edit_{project['id']}", use_container_width=True):
            st.session_state[f"editing_{project['id']}"] = True
            st.rerun()
        
        # Delete with confirmation
        if st.session_state.get(f"confirm_delete_{project['id']}", False):
            if st.button("⚠️ Confirmar Eliminar", key=f"confirm_del_{project['id']}", 
                        use_container_width=True, type="primary"):
                SessionManager.delete_project(project['id'])
                st.session_state[f"confirm_delete_{project['id']}"] = False
                st.success("Proyecto eliminado")
                st.rerun()
        else:
            if st.button("🗑️ Eliminar", key=f"delete_{project['id']}", use_container_width=True):
                st.session_state[f"confirm_delete_{project['id']}"] = True
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Edit form (if editing)
    if st.session_state.get(f"editing_{project['id']}", False):
        with st.expander("✏️ Editar Proyecto", expanded=True):
            with st.form(f"edit_form_{project['id']}"):
                new_name = st.text_input("Nombre", value=project['name'])
                new_status = st.selectbox(
                    "Estado",
                    options=['En Progreso', 'Completado', 'Pausado'],
                    index=['En Progreso', 'Completado', 'Pausado'].index(project['status'])
                )
                new_notes = st.text_area("Notas", value=project.get('notes', ''), height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Guardar", use_container_width=True, type="primary"):
                        SessionManager.update_project(project['id'], {
                            'name': new_name,
                            'status': new_status,
                            'notes': new_notes
                        })
                        st.session_state[f"editing_{project['id']}"] = False
                        st.success("Proyecto actualizado")
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state[f"editing_{project['id']}"] = False
                        st.rerun()
    
    # Show details if it's the current project
    if SessionManager.get_current_project() and SessionManager.get_current_project()['id'] == project['id']:
        with st.expander("📋 Detalles Completos", expanded=False):
            render_full_project_details(project)


def render_full_project_details(project):
    """Muestra detalles completos del proyecto"""
    
    tab1, tab2, tab3 = st.tabs(["📊 Información", "📄 Documentos", "📈 Reportes"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Información General**")
            st.write(f"**ID:** `{project['id']}`")
            st.write(f"**Nombre:** {project['name']}")
            st.write(f"**Dirección:** {project['address']}")
            st.write(f"**Municipio:** {project['municipality']}")
        
        with col2:
            st.markdown("**Estado del Proyecto**")
            st.write(f"**Estado:** {project['status']}")
            st.write(f"**Fase 1:** {'✅ Completada' if project.get('phase1_completed') else '⭕ Pendiente'}")
            st.write(f"**Creado:** {project['created_date'][:10]}")
            st.write(f"**Modificado:** {project['last_modified'][:10]}")
        
        if project.get('notes'):
            st.markdown("**Notas:**")
            st.info(project['notes'])
    
    with tab2:
        if project.get('documents'):
            st.markdown("**Documentos Subidos:**")
            for doc_type, doc_info in project['documents'].items():
                st.markdown(f"- **{doc_type}:** `{doc_info['filename']}`")
                st.caption(f"Subido: {doc_info['uploaded_date'][:10]}")
        else:
            st.info("No hay documentos subidos en este proyecto")
    
    with tab3:
        if project.get('reports'):
            st.markdown("**Reportes Generados:**")
            for i, report in enumerate(project['reports']):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{report['type']}** - {report['generated_date'][:10]}")
                with col2:
                    st.download_button(
                        label="📥 Descargar",
                        data=report['data'],
                        file_name=f"{report['type']}_{i}.pdf",
                        mime="application/pdf",
                        key=f"dl_report_{project['id']}_{i}"
                    )
        else:
            st.info("No hay reportes generados para este proyecto")