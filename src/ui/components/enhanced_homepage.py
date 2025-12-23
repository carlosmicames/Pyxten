"""
Enhanced Homepage - Natural Language Use Validation
Uses integrated validator with ArcGIS + POT equivalency + NL parsing
"""

import streamlit as st
from src.validators.integrated_validator import IntegratedZoningValidator
from src.database.rules_loader import RulesDatabase
from src.services.session_manager import SessionManager


def render_enhanced_homepage(rules_db):
    """
    Enhanced homepage with natural language use input
    """
    
    SessionManager.initialize()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827; margin-bottom: 0.5rem;">
            Validación Inteligente con Lenguaje Natural
        </h1>
        <p style="font-size: 1.2rem; color: #6b7280;">
            Describe tu proyecto en tus propias palabras - el sistema hará el resto
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Info card explaining how it works
    with st.expander("💡 ¿Cómo funciona?", expanded=False):
        st.markdown("""
        ### El sistema automáticamente:
        
        1. **🗺️ Valida tu dirección** con Google Maps
        2. **📍 Obtiene la zonificación** desde MIPR (Junta de Planificación)
        3. **🔄 Traduce códigos POT** municipales a Reglamento Conjunto
        4. **🧠 Interpreta tu descripción** usando IA
        5. **✅ Valida compatibilidad** con el Reglamento Conjunto 2023
        6. **⚠️ Detecta zonas sobrepuestas** (históricas, costaneras, inundación)
        7. **📊 Genera reporte completo** con recomendaciones
        
        **Objetivo de precisión: 95%+**
        """)
    
    # Check validation limit
    if not SessionManager.can_validate():
        st.error("""
        ### Has alcanzado el límite de validaciones gratuitas
        
        Actualiza a Plan Profesional para validaciones ilimitadas.
        """)
        
        if st.button("🚀 Ver Planes", type="primary"):
            st.session_state.current_page = 'pricing'
            st.rerun()
        return
    
    # Main form
    st.markdown("""
    <div style="background: white; padding: 2.5rem; border-radius: 16px; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); max-width: 900px; margin: 0 auto;">
    """, unsafe_allow_html=True)
    
    st.markdown("### Información del Proyecto")
    
    # Address input
    property_address = st.text_input(
        "Dirección de la Propiedad *",
        placeholder="Ej: Calle Luna 123, Urb. San Patricio",
        help="El sistema validará la dirección con Google Maps",
        key="nl_address"
    )
    
    # Municipality
    municipality = st.selectbox(
        "Municipio *",
        options=[""] + rules_db.get_municipalities(),
        help="Municipio donde se ubica la propiedad",
        index=0
    )
    
    # Natural language use description
    st.markdown("### Describe tu Proyecto")
    st.caption("Escribe en tus propias palabras qué quieres hacer:")
    
    use_description = st.text_area(
        "¿Qué tipo de uso o construcción deseas?",
        placeholder="Ejemplos:\n"
                   "• 'Quiero construir una residencia con un edificio para una panadería'\n"
                   "• 'Voy a operar una lavandería y una oficina profesional'\n"
                   "• 'Hotel boutique pequeño con restaurante en la planta baja'\n"
                   "• 'Finca agrícola con casa familiar'",
        height=120,
        help="Describe tu proyecto de forma natural - el sistema lo interpretará automáticamente",
        label_visibility="collapsed"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Validate button
    col1, col2 = st.columns([2, 1])
    
    with col1:
        validate_button = st.button(
            "🚀 Validar Proyecto con IA",
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        remaining = SessionManager.get_remaining_validations()
        st.caption(f"📊 {remaining} validaciones restantes")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Validation logic
    if validate_button:
        if not all([property_address, municipality, use_description]):
            st.error("⚠️ Por favor completa todos los campos marcados con *")
        else:
            # Create integrated validator
            validator = IntegratedZoningValidator(rules_db)
            
            # Show progress
            progress_placeholder = st.empty()
            steps_placeholder = st.empty()
            
            with progress_placeholder.container():
                st.info("🔄 Procesando validación...")
            
            with steps_placeholder.container():
                with st.expander("Ver progreso en tiempo real", expanded=True):
                    step_status = {
                        "1. Geocodificando dirección": "⏳",
                        "2. Consultando MIPR (zonificación)": "⏳",
                        "3. Verificando POT municipal": "⏳",
                        "4. Interpretando uso con IA": "⏳",
                        "5. Validando compatibilidad": "⏳",
                        "6. Verificando zonas sobrepuestas": "⏳",
                        "7. Generando reporte": "⏳"
                    }
                    
                    status_display = st.empty()
                    status_display.markdown("\n".join([f"{k}: {v}" for k, v in step_status.items()]))
            
            # Run validation
            try:
                result = validator.validate_from_natural_language(
                    address=property_address,
                    municipality=municipality,
                    use_description=use_description
                )
                
                # Update session
                SessionManager.add_validation_to_history(result)
                
                # Clear progress
                progress_placeholder.empty()
                steps_placeholder.empty()
                
                # Render results
                render_enhanced_results(result, rules_db)
                
            except Exception as e:
                progress_placeholder.empty()
                steps_placeholder.empty()
                
                st.error(f"❌ Error durante validación: {str(e)}")
                
                with st.expander("Ver detalles del error"):
                    st.exception(e)


def render_enhanced_results(result: dict, rules_db):
    """Render enhanced validation results with detailed breakdown"""
    
    st.markdown("---")
    st.markdown("## 📊 Resultados de Validación")
    
    # Confidence score prominently displayed
    confidence = result['confidence']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        confidence_color = "#10b981" if confidence['overall'] >= 0.95 else "#f59e0b" if confidence['overall'] >= 0.80 else "#ef4444"
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; text-align: center;
                    border: 3px solid {confidence_color};">
            <div style="font-size: 0.9rem; color: #6b7280; margin-bottom: 0.5rem;">
                Confianza General
            </div>
            <div style="font-size: 2.5rem; font-weight: 800; color: {confidence_color};">
                {confidence['overall']*100:.1f}%
            </div>
            <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
                {'✅ Cumple objetivo 95%' if confidence['meets_95_percent_target'] else '⚠️ Por debajo de objetivo'}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        uses_count = result['final_result'].get('total_uses', 0)
        st.metric("Usos Identificados", uses_count)
    
    with col3:
        overlays_count = len(result['steps']['2_arcgis_lookup'].get('overlays', []))
        st.metric("Zonas Sobrepuestas", overlays_count)
    
    # Data sources used
    with st.expander("📚 Fuentes de Datos Utilizadas"):
        for source in result['data_sources']:
            st.markdown(f"""
            **{source['source']}**
            - Propósito: {source['purpose']}
            - Timestamp: {source['timestamp'][:19]}
            """)
            
            if source.get('last_updated'):
                st.caption(f"Última actualización: {source['last_updated']}")
            
            if source.get('freshness_warning'):
                st.warning(source['freshness_warning'])
    
    # Warnings
    if result['warnings']:
        st.markdown("### ⚠️ Advertencias Importantes")
        for warning in result['warnings']:
            st.warning(warning)
    
    # Step-by-step breakdown
    with st.expander("🔍 Desglose Paso a Paso", expanded=False):
        st.markdown("#### Paso 1: Geocodificación")
        geocode = result['steps']['1_geocoding']
        if geocode['success']:
            st.success(f"✅ Dirección validada: {geocode['formatted_address']}")
            st.caption(f"Coordenadas: {geocode['coordinates']['latitude']:.6f}, {geocode['coordinates']['longitude']:.6f}")
        else:
            st.error(f"❌ {geocode['error']}")
        
        st.markdown("#### Paso 2: Consulta ArcGIS (MIPR)")
        arcgis = result['steps']['2_arcgis_lookup']
        if arcgis['success']:
            zoning = arcgis['zoning']
            st.success(f"✅ Zonificación: {zoning['district_code']} - {zoning['district_name']}")
            st.caption(f"Fuente: {zoning['source']} | Última actualización: {zoning.get('last_updated', 'N/A')}")
            
            if arcgis['overlays']:
                st.info(f"🗺️ {len(arcgis['overlays'])} zona(s) sobrepuesta(s) detectada(s)")
        else:
            st.error(f"❌ {arcgis['error']}")
        
        st.markdown("#### Paso 3: Equivalencia POT")
        pot = result['steps']['3_pot_equivalency']
        if pot['needs_equivalency']:
            st.info(f"🔄 Distrito municipal '{pot['original_district']}' mapeado a RC 2020: '{pot['final_zoning_code']}'")
        else:
            st.success(f"✅ Distrito ya usa códigos RC 2020: '{pot['final_zoning_code']}'")
        
        st.markdown("#### Paso 4: Clasificación de Uso (IA)")
        use_class = result['steps']['4_use_classification']
        if use_class.get('uses'):
            for use in use_class['uses']:
                confidence_emoji = "🟢" if use['confidence'] >= 0.9 else "🟡" if use['confidence'] >= 0.7 else "🔴"
                st.markdown(f"{confidence_emoji} **{use['code']}**: {use['name']} (confianza: {use['confidence']*100:.0f}%)")
                st.caption(f"Interpretación: {use['interpretation']}")
        
        st.markdown("#### Paso 5: Validación de Compatibilidad")
        compat = result['steps']['5_compatibility_validation']
        if compat['all_uses_compatible']:
            st.success("✅ Todos los usos son compatibles")
        else:
            st.error("❌ Algunos usos no son compatibles")
        
        st.markdown("#### Paso 6: Restricciones por Zonas Sobrepuestas")
        overlays = result['steps']['6_overlay_restrictions']
        if overlays['has_overlays']:
            for restriction in overlays['restrictions']:
                severity_emoji = "🚫" if restriction['severity'] == 'high' else "⚠️"
                st.warning(f"{severity_emoji} **{restriction['overlay']}**: {restriction['restriction']}")
        else:
            st.success("✅ No hay restricciones adicionales por zonas sobrepuestas")
    
    # Final result
    st.markdown("---")
    final = result['final_result']
    
    if final['viable']:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                    border: 3px solid #10b981; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">✅</div>
            <div style="font-size: 2rem; font-weight: 800; color: #065f46;">
                PROYECTO VIABLE
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                    border: 3px solid #ef4444; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-size: 2rem; font-weight: 800; color: #991b1b;">
                PROYECTO NO VIABLE
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.info(final['summary'])
    
    # Uses validated
    st.markdown("### Usos Validados")
    for use in final['uses_validated']:
        with st.expander(f"{use['name']} ({use['code']})"):
            st.markdown(f"**Interpretación:** {use['interpretation']}")
            st.markdown(f"**Confianza:** {use['confidence']*100:.0f}%")
            st.markdown(f"**Categoría:** {use['category']}")
            st.markdown(f"**Zonas compatibles:** {', '.join(use['compatible_zones'])}")
            st.markdown(f"**Ministerial:** {'Sí' if use['ministerial'] else 'No'}")
    
    # Recommendations
    st.markdown("### 💡 Recomendaciones")
    for rec in final['recommendations']:
        st.markdown(f"- {rec}")
    
    # Next steps
    st.markdown("### 📋 Próximos Pasos")
    for i, step in enumerate(final['next_steps'], 1):
        st.markdown(f"{step}")
    
    # Download report button
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Descargar Reporte Completo (PDF)", use_container_width=True):
            st.info("📄 Generación de PDF disponible próximamente")
    
    with col2:
        if st.button("🔄 Nueva Validación", use_container_width=True):
            st.rerun()


# For testing
if __name__ == "__main__":
    from src.database.rules_loader import RulesDatabase
    
    st.set_page_config(page_title="Pyxten - NL Validation", layout="wide")
    
    rules_db = RulesDatabase()
    render_enhanced_homepage(rules_db)