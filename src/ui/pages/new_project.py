# Pagina para crear nuevo proyecto
import streamlit as st
import os
from src.database.rules_loader import RulesDatabase
from src.services.session_manager import SessionManager

def render_new_project_page(rules_db):
    """Página dedicada para crear nuevo proyecto"""
    
    SessionManager.initialize()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827;">
            ➕ Crear Nuevo Proyecto
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Organiza y gestiona tus proyectos de construcción
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Form in a clean card
    st.markdown("""
    <div style="background: white; padding: 2.5rem; border-radius: 16px; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); max-width: 800px; margin: 0 auto;">
    """, unsafe_allow_html=True)
    
    with st.form("create_project_form", clear_on_submit=True):
        st.markdown("### 📋 Información Básica")
        
        project_name = st.text_input(
            "Nombre del Proyecto *",
            placeholder="Ej: Residencia Familia García",
            help="Nombre descriptivo para identificar fácilmente el proyecto"
        )
        
        project_address = st.text_input(
            "Dirección de la Propiedad *",
            placeholder="Ej: Calle Luna 123, Urb. San Patricio",
            help="Dirección completa de la propiedad"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_municipality = st.selectbox(
                "Municipio *",
                options=[""] + rules_db.get_municipalities(),
                help="Municipio donde se ubica la propiedad"
            )
        
        with col2:
            project_type = st.selectbox(
                "Tipo de Proyecto",
                options=[
                    "",
                    "Residencial",
                    "Comercial",
                    "Industrial",
                    "Mixto",
                    "Otro"
                ]
            )
        
        st.markdown("### 📝 Descripción (Opcional)")
        
        project_description = st.text_area(
            "Descripción",
            placeholder="Describe brevemente el proyecto, objetivos, fase actual, etc.",
            height=100,
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
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
                # Try Supabase first, fall back to SessionManager
                project_id = None

                if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY") and st.session_state.get('user'):
                    try:
                        from src.services.supabase_client import SupabaseService

                        supabase = SupabaseService()
                        user_id = st.session_state.user.id

                        project_data = {
                            'name': project_name,
                            'address': project_address,
                            'municipality': project_municipality,
                            'project_type': project_type if project_type else None,
                            'notes': project_description if project_description else None
                        }

                        project = supabase.create_project(user_id, project_data)
                        if project:
                            project_id = project['id']
                            st.session_state.current_project_id = project_id

                    except Exception as e:
                        st.warning(f"Error con Supabase, usando almacenamiento local: {e}")
                        project_id = None

                # Fallback to SessionManager
                if not project_id:
                    project_id = SessionManager.create_project(
                        name=project_name,
                        address=project_address,
                        municipality=project_municipality
                    )

                    # Update with additional info
                    updates = {}
                    if project_type:
                        updates['project_type'] = project_type
                    if project_description:
                        updates['notes'] = project_description

                    if updates:
                        SessionManager.update_project(project_id, updates)

                st.success(f"Proyecto '{project_name}' creado exitosamente!")
                
                st.markdown("""
                <div style="background: #ecfdf5; border-left: 4px solid #10b981; 
                            padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <strong style="color: #065f46;">🎉 ¿Qué sigue?</strong><br>
                    <span style="color: #047857;">
                    • Valida tu proyecto en la página principal<br>
                    • Ve al Dashboard para ver el progreso<br>
                    • Sube documentos cuando estén listos
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🏠 Ir al Homepage", key="goto_home"):
                        st.session_state.current_page = 'homepage'
                        st.rerun()
                
                with col2:
                    if st.button("📊 Ir al Dashboard", key="goto_dash"):
                        st.session_state.current_page = 'dashboard'
                        st.rerun()
                
                with col3:
                    if st.button("📁 Ver Proyectos", key="goto_projects"):
                        st.session_state.current_page = 'active_projects'
                        st.rerun()
                
            else:
                st.error("⚠️ Por favor completa todos los campos marcados con *")
        
        if cancel:
            st.session_state.current_page = 'homepage'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tips section
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📋</div>
            <div style="font-weight: 700; color: #374151; margin-bottom: 0.5rem;">
                Organiza tu Trabajo
            </div>
            <div style="font-size: 0.9rem; color: #6b7280;">
                Mantén todos tus documentos y validaciones en un solo lugar
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🚀</div>
            <div style="font-weight: 700; color: #374151; margin-bottom: 0.5rem;">
                Acelera tu Proceso
            </div>
            <div style="font-size: 0.9rem; color: #6b7280;">
                Valida antes de someter y ahorra tiempo en correcciones
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">💡</div>
            <div style="font-weight: 700; color: #374151; margin-bottom: 0.5rem;">
                Evita Rechazos
            </div>
            <div style="font-size: 0.9rem; color: #6b7280;">
                Identifica problemas antes de que se conviertan en retrasos
            </div>
        </div>
        """, unsafe_allow_html=True)