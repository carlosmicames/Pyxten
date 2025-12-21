"""
Enhanced PCOC Validation Page with:
- Interactive Section 2.1.9 questionnaire
- Confidence scores display
- Document re-upload functionality
"""

import streamlit as st
from src.services.session_manager import SessionManager
from src.validators.pcoc_validator import PCOCValidator
from src.utils.address_validator import AddressValidator
from src.ui.components.section_questionnaire import Section219Questionnaire

def render_pcoc_validator(rules_db, model_router):
    """Enhanced PCOC validation wizard"""
    
    SessionManager.initialize()
    
    st.markdown("## Validación PCOC - Permiso de Construcción Completo")
    
    # Removed paywall check for testing - defaulting to professional access
    
    # Inicializar wizard con paso del cuestionario
    if 'pcoc_step' not in st.session_state:
        st.session_state.pcoc_step = 0  # Starts at questionnaire
    
    if 'pcoc_project_data' not in st.session_state:
        st.session_state.pcoc_project_data = {}
    
    if 'pcoc_uploaded_docs' not in st.session_state:
        st.session_state.pcoc_uploaded_docs = {}
    
    # Progress bar - NOW 5 STEPS
    steps = ["Cuestionario 2.1.9", "Proyecto", "Documentos", "Planos", "Resultados"]
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
        render_questionnaire_step()
    elif st.session_state.pcoc_step == 1:
        render_project_info_step(rules_db)
    elif st.session_state.pcoc_step == 2:
        render_documents_step()
    elif st.session_state.pcoc_step == 3:
        render_planos_step(model_router)
    elif st.session_state.pcoc_step == 4:
        render_results_step_enhanced(rules_db, model_router)


def render_questionnaire_step():
    """Step 0: Interactive Section 2.1.9 questionnaire"""
    
    questionnaire = Section219Questionnaire()
    
    # Render the questionnaire
    is_complete = questionnaire.render()
    
    # Navigation
    st.markdown("---")
    
    if is_complete:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col3:
            if st.button("Continuar a Información del Proyecto →", type="primary", use_container_width=True):
                st.session_state.pcoc_step = 1
                st.rerun()


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
                
                st.session_state.pcoc_step = 2
                st.rerun()
            else:
                st.error("Completa todos los campos marcados con *")
    
    # Back button
    st.markdown("---")
    if st.button("⬅️ Volver al Cuestionario", key="back_to_questionnaire"):
        st.session_state.pcoc_step = 0
        st.rerun()


def render_documents_step():
    """Paso 2: Upload de documentos"""
    
    st.markdown("### 📄 Documentos Requeridos")
    st.info("Sube los documentos básicos. En el próximo paso subirás los planos.")
    
    doc_types = {
        "certificacion_registral": "Certificación Registral (< 90 días)",
        "formulario_ogpe": "Formulario OGPe Completado",
        "certificacion_aaa": "Certificación AAA"
    }
    
    uploaded_any = False
    
    for key, name in doc_types.items():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded = st.file_uploader(
                name,
                type=['pdf', 'jpg', 'png'],
                key=f"doc_{key}"
            )
            
            if uploaded:
                st.session_state.pcoc_uploaded_docs[key] = uploaded.read()
                uploaded_any = True
        
        with col2:
            if key in st.session_state.pcoc_uploaded_docs:
                st.success("✅ Cargado")
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            st.session_state.pcoc_step = 1
            st.rerun()
    
    with col3:
        if uploaded_any:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                st.session_state.pcoc_step = 3
                st.rerun()
        else:
            st.button("Sube al menos un documento", disabled=True, use_container_width=True)


def render_planos_step(model_router):
    """Paso 3: Upload y análisis de planos CON CONFIDENCE SCORES"""
    
    st.markdown("### 📐 Planos de Construcción")
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
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Re-upload functionality
            if key in st.session_state.planos_analyzed:
                if st.button(f"🔄 Re-subir {name}", key=f"reupload_{key}"):
                    # Clear previous analysis
                    del st.session_state.planos_analyzed[key]
                    if key in st.session_state.pcoc_uploaded_docs:
                        del st.session_state.pcoc_uploaded_docs[key]
                    st.rerun()
            
            uploaded = st.file_uploader(
                "Selecciona archivo",
                type=['pdf', 'jpg', 'png'],
                key=f"plano_{key}",
                label_visibility="collapsed"
            )
        
        with col2:
            if uploaded and key not in st.session_state.planos_analyzed:
                if st.button(f"Analizar", key=f"analyze_{key}"):
                    with st.spinner(f"Analizando con IA..."):
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
        
        with col3:
            if key in st.session_state.planos_analyzed:
                result = st.session_state.planos_analyzed[key]
                score = result.get('score', 0)
                confidence = result.get('confidence', 0)
                
                # Display score with color coding
                if score >= 0.9:
                    st.success(f"✅ {score*100:.0f}%")
                elif score >= 0.7:
                    st.warning(f"⚠️ {score*100:.0f}%")
                else:
                    st.error(f"❌ {score*100:.0f}%")
                
                st.caption(f"Confianza: {confidence*100:.0f}%")
        
        # Detailed analysis expandable
        if key in st.session_state.planos_analyzed:
            with st.expander("📊 Ver Análisis Detallado con Confidence Scores"):
                result = st.session_state.planos_analyzed[key]
                
                # Overall metrics
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric("Score General", f"{result.get('score', 0)*100:.0f}%")
                
                with col_b:
                    st.metric("Confianza IA", f"{result.get('confidence', 0)*100:.0f}%")
                
                with col_c:
                    st.metric("Modelo", result.get('model_used', 'unknown'))
                
                st.markdown("---")
                
                # Section 2.1.9 Requirements with confidence
                st.markdown("**Validaciones Sección 2.1.9:**")
                for val in result.get('validations', []):
                    icon = "✅" if val['passed'] else "❌"
                    
                    # Display check with confidence if available
                    check_text = f"{icon} **{val['check']}**"
                    
                    if 'confidence' in val:
                        check_text += f" (Confianza: {val['confidence']*100:.0f}%)"
                    
                    st.markdown(check_text)
                    st.caption(val.get('details', ''))
                    
                    if 'location' in val:
                        st.caption(f"📍 {val['location']}")
                
                # Datos extraídos
                if result.get('extracted_data'):
                    st.markdown("---")
                    st.markdown("**Datos Extraídos:**")
                    for k, v in result['extracted_data'].items():
                        st.markdown(f"- **{k}:** {v}")
                
                # Issues
                if result.get('issues'):
                    st.markdown("---")
                    st.warning("**Issues Detectados:**")
                    for issue in result['issues']:
                        st.markdown(f"- {issue}")
                
                # Critical issues
                if result.get('critical_issues'):
                    st.markdown("---")
                    st.error("**Issues Críticos - Requieren Corrección:**")
                    for issue in result['critical_issues']:
                        st.markdown(f"- ⚠️ {issue}")
                
                # Cost
                st.markdown("---")
                st.caption(f"💰 Costo de análisis: ${result.get('cost_estimate', 0):.4f}")
        
        st.divider()
    
    # Navegación
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True):
            st.session_state.pcoc_step = 2
            st.rerun()
    
    with col3:
        required_analyzed = all(
            key in st.session_state.planos_analyzed
            for key in plano_types.keys()
        )
        
        if required_analyzed:
            if st.button("Ver Resultados →", type="primary", use_container_width=True):
                st.session_state.pcoc_step = 4
                st.rerun()
        else:
            st.button("Analiza todos los planos requeridos", disabled=True, use_container_width=True)


def render_results_step_enhanced(rules_db, model_router):
    """Paso 4: Resultados con confidence scores y re-upload"""
    
    st.markdown("### 📊 Resultados de Validación PCOC")
    
    # Crear validator y validar
    validator = PCOCValidator(model_router, rules_db)
    
    with st.spinner("Generando reporte completo..."):
        results = validator.validate_full_pcoc(
            project_data=st.session_state.pcoc_project_data,
            uploaded_docs=st.session_state.pcoc_uploaded_docs
        )
    
    # Mostrar score general con confianza promedio
    score = results['overall_score']
    
    # Calculate average confidence
    confidences = [
        doc.get('confidence', 0)
        for doc in results['document_scores'].values()
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Display overall metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if score >= 0.90:
            st.success(f"### ✅ {score*100:.0f}%")
            st.caption("Validación Exitosa")
        elif score >= 0.70:
            st.warning(f"### ⚠️ {score*100:.0f}%")
            st.caption("Requiere Correcciones")
        else:
            st.error(f"### ❌ {score*100:.0f}%")
            st.caption("No Cumple")
    
    with col2:
        st.metric("Confianza Promedio IA", f"{avg_confidence*100:.0f}%")
    
    with col3:
        st.metric("Documentos Analizados", len(results['document_scores']))
    
    st.markdown("---")
    
    # Compliance message
    if score >= 0.90:
        st.success("Tu solicitud cumple con los requisitos del Reglamento Conjunto Sección 2.1.9")
    elif score >= 0.70:
        st.warning("Tu solicitud necesita ajustes menores antes de someter")
    else:
        st.error("Tu solicitud tiene issues críticos que deben corregirse")
    
    # Mostrar dirección validada
    if st.session_state.pcoc_project_data.get('address_data'):
        addr_data = st.session_state.pcoc_project_data['address_data']
        with st.expander("📍 Dirección Validada"):
            st.info(f"**Dirección:** {addr_data['formatted_address']}")
            st.caption(f"Coordenadas: {addr_data['latitude']}, {addr_data['longitude']}")
    
    # Critical blockers
    if results['critical_blockers']:
        st.markdown("---")
        st.error("### 🚫 Issues Críticos que Bloquean Aprobación:")
        for blocker in results['critical_blockers']:
            st.markdown(f"- {blocker}")
    
    # Análisis por documento CON CONFIDENCE
    st.markdown("---")
    st.markdown("### 📄 Análisis Detallado por Documento")
    
    for doc_type, doc_result in results['document_scores'].items():
        with st.expander(f"{doc_type} - Score: {doc_result['score']*100:.0f}% | Confianza: {doc_result.get('confidence', 0)*100:.0f}%"):
            
            # Show re-upload option if score is low
            if doc_result['score'] < 0.9:
                st.warning(f"Este documento no cumple todos los requisitos (score: {doc_result['score']*100:.0f}%)")
                if st.button(f"🔄 Re-subir y Re-analizar {doc_type}", key=f"reupload_result_{doc_type}"):
                    # Return to planos step to re-upload
                    st.session_state.pcoc_step = 3
                    st.rerun()
            
            st.caption(f"Modelo: {doc_result.get('model_used', 'unknown')} | Costo: ${doc_result.get('cost_estimate', 0):.4f}")
            
            st.markdown("**Requisitos Sección 2.1.9:**")
            for val in doc_result.get('validations', []):
                icon = "✅" if val['passed'] else "❌"
                conf_text = f" (Confianza: {val.get('confidence', doc_result.get('confidence', 0))*100:.0f}%)" if 'confidence' in val else ""
                st.markdown(f"{icon} {val['check']}{conf_text}")
                if not val['passed'] and val.get('details'):
                    st.caption(f"⚠️ {val['details']}")
    
    # Recomendaciones
    st.markdown("---")
    st.markdown("### 💡 Recomendaciones")
    for rec in results['recommendations']:
        st.markdown(f"- {rec}")
    
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
        if st.button("📥 Descargar Reporte", use_container_width=True):
            st.info("Generación de PDF disponible en Sprint 2")
    
    with col2:
        if st.button("🔄 Nueva Validación", use_container_width=True):
            # Reset wizard
            st.session_state.pcoc_step = 0
            st.session_state.pcoc_project_data = {}
            st.session_state.pcoc_uploaded_docs = {}
            st.session_state.planos_analyzed = {}
            st.session_state.pcoc_address_validated = False
            st.session_state.questionnaire_answers = {}
            st.session_state.current_question = 'start'
            st.rerun()
    
    with col3:
        if st.button("📊 Ir al Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()