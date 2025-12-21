"""
Página de validación PCOC completa con validación de direcciones
"""

import streamlit as st
from src.services.session_manager import SessionManager
from src.validators.pcoc_validator import PCOCValidator
from src.utils.address_validator import AddressValidator

def render_pcoc_validator(rules_db, model_router):
    """Wizard de validación PCOC"""
    
    SessionManager.initialize()
    
    st.markdown("## Validación PCOC - Permiso de Construcción")
    
    # Verificar acceso
    user_plan = st.session_state.get('user_plan', 'professional')
    
    if user_plan == 'free':
        st.error("Esta función requiere Plan Profesional o superior")
        if st.button("Ver Planes"):
            st.session_state.current_page = 'pricing'
            st.rerun()
        return
    
    # Inicializar wizard
    if 'pcoc_step' not in st.session_state:
        st.session_state.pcoc_step = 0
    
    if 'pcoc_project_data' not in st.session_state:
        st.session_state.pcoc_project_data = {}
    
    if 'pcoc_uploaded_docs' not in st.session_state:
        st.session_state.pcoc_uploaded_docs = {}
    
    # Progress bar
    steps = ["Proyecto", "Documentos", "Planos", "Resultados"]
    progress = (st.session_state.pcoc_step + 1) / len(steps)
    st.progress(progress, text=f"Paso {st.session_state.pcoc_step + 1} de {len(steps)}")
    
    # Indicador de pasos
    cols = st.columns(len(steps))
    for i, step in enumerate(steps):
        with cols[i]:
            if i < st.session_state.pcoc_step:
                st.markdown(f"✅ **{step}**")
            elif i == st.session_state.pcoc_step:
                st.markdown(f"🔵 **{step}**")
            else:
                st.markdown(f"⚪ {step}")
    
    st.divider()
    
    # Renderizar paso actual
    if st.session_state.pcoc_step == 0:
        render_project_info_step(rules_db)
    elif st.session_state.pcoc_step == 1:
        render_documents_step()
    elif st.session_state.pcoc_step == 2:
        render_planos_step(model_router)
    elif st.session_state.pcoc_step == 3:
        render_results_step(rules_db, model_router)


def render_project_info_step(rules_db):
    """Paso 1: Información del proyecto CON VALIDACIÓN DE DIRECCIÓN"""
    
    st.markdown("### 📝 Información del Proyecto")
    st.info("💡 Validaremos tu dirección con Google Maps para asegurar precisión")
    
    with st.form("project_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Nombre del Proyecto *",
                value=st.session_state.pcoc_project_data.get('name', ''),
                placeholder="Ej: Residencia Familia García"
            )
            
            project_address = st.text_input(
                "Dirección *",
                value=st.session_state.pcoc_project_data.get('address', ''),
                placeholder="Calle Luna 123",
                help="Dirección física del proyecto"
            )
        
        with col2:
            municipality = st.selectbox(
                "Municipio *",
                options=[""] + rules_db.get_municipalities(),
                index=0
            )
            
            zoning = st.text_input(
                "Zonificación",
                value=st.session_state.pcoc_project_data.get('zoning', ''),
                placeholder="R-2",
                help="Distrito de zonificación (opcional)"
            )
        
        # Botón de validar dirección
        validate_address_btn = st.form_submit_button(
            "🗺️ Validar Dirección con Google Maps",
            use_container_width=True
        )
        
        submitted = st.form_submit_button(
            "Siguiente →", 
            type="primary", 
            use_container_width=True
        )
        
        # Validar dirección con Google Maps
        if validate_address_btn:
            if project_address and municipality:
                with st.spinner("Validando dirección con Google Maps..."):
                    try:
                        address_validator = AddressValidator()
                        result = address_validator.validate_address(
                            address=project_address,
                            municipality=municipality
                        )
                        
                        if result['valid']:
                            st.success("✅ Dirección válida")
                            
                            # Mostrar dirección formateada
                            st.info(f"**Dirección completa:**\n{result['formatted_address']}")
                            
                            # Mostrar coordenadas
                            with st.expander("Ver Coordenadas"):
                                st.write(f"**Latitud:** {result['latitude']}")
                                st.write(f"**Longitud:** {result['longitude']}")
                                st.write(f"**Precisión:** {result['confidence']}")
                            
                            # Guardar en session state
                            st.session_state.pcoc_address_validated = True
                            st.session_state.pcoc_address_data = result
                            
                            # Advertencia si municipio no coincide
                            if 'warning' in result:
                                st.warning(f"⚠️ {result['warning']}")
                        
                        else:
                            st.error(f"❌ Dirección no válida: {result.get('error', 'Error desconocido')}")
                            st.session_state.pcoc_address_validated = False
                    
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")
                        st.info("Asegúrate de agregar GOOGLE_MAPS_API_KEY en .env")
                    except Exception as e:
                        st.error(f"Error validando dirección: {str(e)}")
                        st.session_state.pcoc_address_validated = False
            else:
                st.warning("Ingresa dirección y municipio primero")
        
        # Continuar al siguiente paso
        if submitted:
            if all([project_name, project_address, municipality]):
                # Guardar datos
                st.session_state.pcoc_project_data = {
                    'name': project_name,
                    'address': project_address,
                    'municipality': municipality,
                    'zoning': zoning
                }
                
                # Agregar datos de Google Maps si están validados
                if st.session_state.get('pcoc_address_validated'):
                    st.session_state.pcoc_project_data['address_data'] = st.session_state.pcoc_address_data
                
                st.session_state.pcoc_step = 1
                st.rerun()
            else:
                st.error("Completa todos los campos marcados con *")


def render_documents_step():
    """Paso 2: Upload de documentos"""
    
    st.markdown("### Documentos Requeridos")
    st.info("Sube los documentos básicos. En el próximo paso subirás los planos.")
    
    doc_types = {
        "certificacion_registral": "Certificación Registral (< 90 días)",
        "formulario_ogpe": "Formulario OGPe Completado",
        "certificacion_aaa": "Certificación AAA"
    }
    
    uploaded_any = False
    
    for key, name in doc_types.items():
        uploaded = st.file_uploader(
            name,
            type=['pdf', 'jpg', 'png'],
            key=f"doc_{key}"
        )
        
        if uploaded:
            st.session_state.pcoc_uploaded_docs[key] = uploaded.read()
            st.success(f"✅ {uploaded.name} cargado")
            uploaded_any = True
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅Anterior", use_container_width=True):
            st.session_state.pcoc_step = 0
            st.rerun()
    
    with col3:
        if uploaded_any:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                st.session_state.pcoc_step = 2
                st.rerun()
        else:
            st.button("Sube al menos un documento", disabled=True, use_container_width=True)


def render_planos_step(model_router):
    """Paso 3: Upload y análisis de planos"""
    
    st.markdown("### Planos de Construcción")
    st.info("La IA analizará automáticamente cada plano que subas")
    
    plano_types = {
        "planta_arquitectonica": "Planta Arquitectónica *",
        "elevaciones": "Elevaciones (4 fachadas) *",
        "planta_conjunto": "Planta de Conjunto *"
    }
    
    if 'planos_analyzed' not in st.session_state:
        st.session_state.planos_analyzed = {}
    
    for key, name in plano_types.items():
        st.markdown(f"#### {name}")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded = st.file_uploader(
                "Selecciona archivo",
                type=['pdf', 'jpg', 'png'],
                key=f"plano_{key}",
                label_visibility="collapsed"
            )
            
            if uploaded and key not in st.session_state.planos_analyzed:
                if st.button(f"Analizar {name}", key=f"analyze_{key}"):
                    with st.spinner(f"Analizando {name} con IA..."):
                        file_bytes = uploaded.read()
                        
                        # Obtener requirements
                        from src.validators.pcoc_validator import PCOCValidator
                        validator = PCOCValidator(model_router, None)
                        requirements = validator.requirements.get(key, {}).get('requirements', [])
                        
                        # Analizar
                        result = model_router.analyze_document(
                            doc_type=key,
                            file_bytes=file_bytes,
                            requirements=requirements
                        )
                        
                        st.session_state.pcoc_uploaded_docs[key] = file_bytes
                        st.session_state.planos_analyzed[key] = result
                        st.rerun()
        
        with col2:
            if key in st.session_state.planos_analyzed:
                result = st.session_state.planos_analyzed[key]
                score = result.get('score', 0)
                model_used = result.get('model_used', 'unknown')
                
                if score >= 0.9:
                    st.success(f"✅ {score*100:.0f}%")
                elif score >= 0.7:
                    st.warning(f"⚠️ {score*100:.0f}%")
                else:
                    st.error(f"❌ {score*100:.0f}%")
                
                st.caption(f"Modelo: {model_used}")
        
        if key in st.session_state.planos_analyzed:
            with st.expander("Ver Análisis Detallado"):
                result = st.session_state.planos_analyzed[key]
                
                # Validaciones
                st.markdown("**Validaciones:**")
                for val in result.get('validations', []):
                    icon = "✅" if val['passed'] else "❌"
                    st.markdown(f"{icon} **{val['check']}**")
                    st.caption(val.get('details', ''))
                
                # Datos extraídos
                if result.get('extracted_data'):
                    st.markdown("**Datos Extraídos:**")
                    for k, v in result['extracted_data'].items():
                        st.markdown(f"- **{k}:** {v}")
                
                # Issues
                if result.get('issues'):
                    st.warning("**Issues Detectados:**")
                    for issue in result['issues']:
                        st.markdown(f"- {issue}")
                
                # Critical issues
                if result.get('critical_issues'):
                    st.error("**Issues Críticos:**")
                    for issue in result['critical_issues']:
                        st.markdown(f"- ⚠️ {issue}")
                
                # Costo y modelo
                st.divider()
                st.caption(f"Costo estimado: ${result.get('cost_estimate', 0):.4f}")
                st.caption(f"Modelo usado: {result.get('model_used', 'unknown')}")
        
        st.divider()
    
    # Navegación
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            st.session_state.pcoc_step = 1
            st.rerun()
    
    with col3:
        required_analyzed = all(
            key in st.session_state.planos_analyzed
            for key in plano_types.keys()
        )
        
        if required_analyzed:
            if st.button("Ver Resultados →", type="primary", use_container_width=True):
                st.session_state.pcoc_step = 3
                st.rerun()
        else:
            st.button("Analiza todos los planos", disabled=True, use_container_width=True)


def render_results_step(rules_db, model_router):
    """Paso 4: Mostrar resultados"""
    
    st.markdown("### Resultados de Validación")
    
    # Crear validator y validar
    validator = PCOCValidator(model_router, rules_db)
    
    with st.spinner("Generando reporte completo..."):
        results = validator.validate_full_pcoc(
            project_data=st.session_state.pcoc_project_data,
            uploaded_docs=st.session_state.pcoc_uploaded_docs
        )
    
    # Mostrar score general
    score = results['overall_score']
    
    if score >= 0.90:
        st.success(f"### Validación Exitosa ({score*100:.0f}%)")
        st.markdown("Tu solicitud cumple con los requisitos del Reglamento Conjunto")
    elif score >= 0.70:
        st.warning(f"### Requiere Correcciones ({score*100:.0f}%)")
        st.markdown("Tu solicitud necesita ajustes menores antes de someter")
    else:
        st.error(f"### No Cumple Requisitos ({score*100:.0f}%)")
        st.markdown("Tu solicitud tiene issues críticos que deben corregirse")
    
    # Mostrar dirección validada si está disponible
    if st.session_state.pcoc_project_data.get('address_data'):
        addr_data = st.session_state.pcoc_project_data['address_data']
        with st.expander("Dirección Validada por Google Maps"):
            st.info(f"**Dirección:** {addr_data['formatted_address']}")
            st.caption(f"Coordenadas: {addr_data['latitude']}, {addr_data['longitude']}")
    
    # Blockers críticos
    if results['critical_blockers']:
        st.markdown("---")
        st.error("**🚫 Issues Críticos (deben corregirse):**")
        for blocker in results['critical_blockers']:
            st.markdown(f"- {blocker}")
    
    # Análisis por documento
    st.markdown("---")
    st.markdown("### 📄 Análisis por Documento")
    
    for doc_type, doc_result in results['document_scores'].items():
        with st.expander(f"{doc_type} - Score: {doc_result['score']*100:.0f}%"):
            st.caption(f"Modelo: {doc_result.get('model_used', 'unknown')} | Costo: ${doc_result.get('cost_estimate', 0):.4f}")
            
            for val in doc_result.get('validations', []):
                icon = "✅" if val['passed'] else "❌"
                st.markdown(f"{icon} {val['check']}")
    
    # Recomendaciones
    st.markdown("---")
    st.markdown("### Recomendaciones")
    for rec in results['recommendations']:
        st.markdown(rec)
    
    # Costo total
    total_cost = sum(
        doc.get('cost_estimate', 0) 
        for doc in results['document_scores'].values()
    )
    st.info(f"**Costo total de análisis IA:** ${total_cost:.4f}")
    
    # Acciones
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Descargar Reporte", use_container_width=True):
            st.info("Generación de PDF disponible en Sprint 2")
    
    with col2:
        if st.button("Nueva Validación", use_container_width=True):
            # Reset wizard
            st.session_state.pcoc_step = 0
            st.session_state.pcoc_project_data = {}
            st.session_state.pcoc_uploaded_docs = {}
            st.session_state.planos_analyzed = {}
            st.session_state.pcoc_address_validated = False
            st.rerun()
    
    with col3:
        if st.button("Ir al Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()