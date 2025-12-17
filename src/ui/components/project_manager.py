# Project Manager Component - Gestión de proyectos
import streamlit as st
from src.services.session_manager import SessionManager
import json

def render_project_manager():
    """Renderiza el gestor de proyectos"""
    
    SessionManager.initialize()
    
    st.markdown("## 📁 Gestor de Proyectos")
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📂 Mis Proyectos", "➕ Nuevo Proyecto", "📤 Exportar"])
    
    with tab1:
        render_projects_list()
    
    with tab2:
        render_new_project_form()
    
    with tab3:
        render_export_options()


def render_projects_list():
    """Lista todos los proyectos"""
    
    projects = SessionManager.get_all_projects()
    
    if not projects:
        st.info("No tienes proyectos creados. Crea uno nuevo en la pestaña 'Nuevo Proyecto'.")
        return
    
    st.markdown(f"**Total de Proyectos:** {len(projects)}")
    st.divider()
    
    for project_id, project in projects.items():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.markdown(f"### {project['name']}")
                st.caption(f"📍 {project['address']}")
                st.caption(f"🏛️ {project['municipality']}")
            
            with col2:
                status_emoji = {
                    'En Progreso': '🟡',
                    'Completado': '🟢',
                    'Pausado': '🔴'
                }.get(project['status'], '⚪')
                
                st.markdown(f"{status_emoji} **{project['status']}**")
                st.caption(f"Creado: {project['created_date'][:10]}")
            
            with col3:
                if st.button("Abrir", key=f"open_{project_id}", use_container_width=True):
                    SessionManager.set_current_project(project_id)
                    st.success(f"Proyecto '{project['name']}' abierto")
                    st.rerun()
            
            with col4:
                if st.button("🗑️", key=f"delete_{project_id}", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{project_id}"):
                        SessionManager.delete_project(project_id)
                        st.success("Proyecto eliminado")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{project_id}"] = True
                        st.warning("Presiona de nuevo para confirmar eliminación")
            
            # Mostrar detalles del proyecto actual
            if SessionManager.get_current_project() and SessionManager.get_current_project()['id'] == project_id:
                with st.expander("📋 Detalles del Proyecto", expanded=True):
                    render_project_details(project)
            
            st.divider()


def render_project_details(project):
    """Muestra detalles completos de un proyecto"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Información Básica**")
        st.write(f"**ID:** `{project['id']}`")
        st.write(f"**Nombre:** {project['name']}")
        st.write(f"**Dirección:** {project['address']}")
        st.write(f"**Municipio:** {project['municipality']}")
        st.write(f"**Estado:** {project['status']}")
    
    with col2:
        st.markdown("**Progreso**")
        st.write(f"**Fase 1 Completada:** {'✅' if project['phase1_completed'] else '❌'}")
        
        if project.get('documents'):
            st.write(f"**Documentos:** {len(project['documents'])}")
        
        if project.get('reports'):
            st.write(f"**Reportes:** {len(project['reports'])}")
        
        st.write(f"**Última Modificación:** {project['last_modified'][:10]}")
    
    # Notas del proyecto
    st.markdown("---")
    st.markdown("**📝 Notas del Proyecto**")
    notes = st.text_area(
        "Notas",
        value=project.get('notes', ''),
        key=f"notes_{project['id']}",
        label_visibility="collapsed",
        height=100
    )
    
    if st.button("💾 Guardar Notas", key=f"save_notes_{project['id']}"):
        SessionManager.update_project(project['id'], {'notes': notes})
        st.success("Notas guardadas")
    
    # Cambiar estado
    st.markdown("---")
    st.markdown("**🔄 Cambiar Estado**")
    new_status = st.selectbox(
        "Estado",
        options=['En Progreso', 'Completado', 'Pausado'],
        index=['En Progreso', 'Completado', 'Pausado'].index(project['status']),
        key=f"status_{project['id']}"
    )
    
    if new_status != project['status']:
        if st.button("Actualizar Estado", key=f"update_status_{project['id']}"):
            SessionManager.update_project(project['id'], {'status': new_status})
            st.success(f"Estado actualizado a '{new_status}'")
            st.rerun()


def render_new_project_form():
    """Formulario para crear nuevo proyecto"""
    
    st.markdown("### Crear Nuevo Proyecto")
    
    with st.form("create_project_form"):
        project_name = st.text_input(
            "Nombre del Proyecto *",
            placeholder="Ej: Residencia Familia García",
            help="Nombre descriptivo para identificar el proyecto"
        )
        
        project_address = st.text_input(
            "Dirección de la Propiedad *",
            placeholder="Ej: Calle Luna 123, Urb. San Patricio",
            help="Dirección completa de la propiedad"
        )
        
        from src.database.rules_loader import RulesDatabase
        rules_db = RulesDatabase()
        
        project_municipality = st.selectbox(
            "Municipio *",
            options=[""] + rules_db.get_municipalities(),
            help="Municipio donde se ubica la propiedad"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button(
                "✅ Crear Proyecto",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            cancel = st.form_submit_button(
                "❌ Cancelar",
                use_container_width=True
            )
        
        if submitted:
            if all([project_name, project_address, project_municipality]):
                project_id = SessionManager.create_project(
                    name=project_name,
                    address=project_address,
                    municipality=project_municipality
                )
                
                st.success(f"✅ Proyecto '{project_name}' creado exitosamente!")
                st.info(f"ID del Proyecto: `{project_id}`")
                
                # Navigate to dashboard
                if st.button("Ir al Dashboard"):
                    SessionManager.navigate_to('dashboard')
                    st.rerun()
            else:
                st.error("⚠️ Por favor completa todos los campos marcados con *")
        
        if cancel:
            SessionManager.navigate_to('dashboard')
            st.rerun()


def render_export_options():
    """Opciones de exportación de proyectos"""
    
    st.markdown("### 📤 Exportar Proyectos")
    
    projects = SessionManager.get_all_projects()
    
    if not projects:
        st.info("No tienes proyectos para exportar.")
        return
    
    st.markdown("""
    Exporta tus proyectos para:
    - 💾 Hacer backup
    - 📧 Compartir con tu equipo
    - 📂 Guardar para referencia futura
    
    **Nota:** Los archivos grandes (PDFs, documentos) no se incluyen en la exportación.
    Solo se exportan metadatos y configuraciones.
    """)
    
    export_option = st.radio(
        "¿Qué deseas exportar?",
        options=[
            "Todos los proyectos",
            "Proyecto específico",
            "Proyecto actual"
        ]
    )
    
    if export_option == "Todos los proyectos":
        export_data = {
            pid: SessionManager.export_project(pid)
            for pid in projects.keys()
        }
        
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📥 Descargar Todos los Proyectos (JSON)",
            data=json_data,
            file_name="pyxten_todos_proyectos.json",
            mime="application/json",
            use_container_width=True
        )
    
    elif export_option == "Proyecto específico":
        project_options = {
            f"{p['name']} ({p['id']})": p['id']
            for p in projects.values()
        }
        
        selected = st.selectbox(
            "Selecciona el proyecto",
            options=list(project_options.keys())
        )
        
        if selected and st.button("Exportar Proyecto Seleccionado"):
            project_id = project_options[selected]
            export_data = SessionManager.export_project(project_id)
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label=f"📥 Descargar '{selected}' (JSON)",
                data=json_data,
                file_name=f"pyxten_proyecto_{project_id}.json",
                mime="application/json",
                use_container_width=True
            )
    
    elif export_option == "Proyecto actual":
        current = SessionManager.get_current_project()
        
        if current:
            export_data = SessionManager.export_project(current['id'])
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label=f"📥 Descargar '{current['name']}' (JSON)",
                data=json_data,
                file_name=f"pyxten_proyecto_{current['id']}.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.warning("No hay un proyecto actual seleccionado. Abre un proyecto primero.")