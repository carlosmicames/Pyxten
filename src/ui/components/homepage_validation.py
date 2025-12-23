"""
Simplified Phase 1 Homepage - Single Page Validation
2-Column Layout: Ubicación + Proyecto
"""

import streamlit as st
import json
from pathlib import Path
from src.database.rules_loader import RulesDatabase
from src.validators.zoning_validator import ZoningValidator
from src.utils.report_generator import ReportGenerator
from src.services.session_manager import SessionManager
from src.utils.address_validator import AddressValidator

def load_uso_types():
    """Load comprehensive uso types from JSON"""
    # Go up 4 levels from src/ui/components/file.py to project root
    root_dir = Path(__file__).parent.parent.parent.parent
    data_path = root_dir / "data" / "regulations" / "uso_types_comprehensive.json"
    
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def detect_regime(municipality: str) -> dict:
    """Auto-detect applicable regulation based on municipality"""
    
    # Municipalities with POT (Plan de Ordenamiento Territorial)
    pot_municipalities = [
        "San Juan", "Bayamón", "Carolina", "Ponce", "Caguas",
        "Mayagüez", "Guaynabo", "Arecibo", "Toa Baja", "Trujillo Alto"
    ]
    
    # Municipalities with special plans
    special_plans = {
        "Vieques": "Plan Especial Isla de Vieques",
        "Culebra": "Plan Especial Isla de Culebra",
        "Loíza": "Plan de Área Piñones"
    }
    
    if municipality in special_plans:
        return {
            "type": "Plan Especial",
            "name": special_plans[municipality],
            "applies": True
        }
    elif municipality in pot_municipalities:
        return {
            "type": "POT",
            "name": f"Plan de Ordenamiento Territorial - {municipality}",
            "applies": True
        }
    else:
        return {
            "type": "Reglamento Conjunto",
            "name": "Reglamento Conjunto 2023",
            "applies": True
        }

def render_homepage(rules_db, claude_ai=None, model_router=None):
    """Simplified Phase 1 validation - single page, 2 columns"""
    
    SessionManager.initialize()
    uso_data = load_uso_types()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827;">
            Validación Rápida de Zonificación
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Verifica si tu proyecto cumple con Tomo 6 en minutos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check validation limit
    if not SessionManager.can_validate():
        st.error("""
        ### Has alcanzado el límite de validaciones gratuitas
        
        Actualiza a Plan Profesional para validaciones ilimitadas
        """)
        
        if st.button("🚀 Ver Planes", type="primary"):
            st.session_state.current_page = 'pricing'
            st.rerun()
        return
    
    # Show remaining validations if low
    remaining = SessionManager.get_remaining_validations()
    if remaining <= 2:
        st.warning(f"⚠️ Te quedan {remaining} validaciones gratuitas este mes")
    
    # Main form container
    st.markdown("""
    <div style="background: white; padding: 2rem; border-radius: 16px; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);">
    """, unsafe_allow_html=True)
    
    # TWO COLUMNS: Ubicación + Proyecto
    col_left, col_right = st.columns(2)
    
    # === LEFT COLUMN: UBICACIÓN ===
    with col_left:
        st.markdown("### 📍 Paso 1: Ubicación")
        st.markdown("---")
        
        # Address input
        property_address = st.text_input(
            "Dirección de la Propiedad *",
            placeholder="Ej: Calle Luna 123, Urb. San Patricio",
            help="Dirección completa de la propiedad",
            key="address_input"
        )
        
        # Municipality (will auto-fill after validation)
        municipality = st.selectbox(
            "Municipio *",
            options=[""] + rules_db.get_municipalities(),
            help="Selecciona el municipio",
            key="municipality_input"
        )
        
        # Address Validation Button
        if property_address and municipality:
            if st.button("🗺️ Validar Dirección", key="validate_address_btn", use_container_width=True):
                with st.spinner("Validando dirección con Google Maps..."):
                    try:
                        address_validator = AddressValidator()
                        result = address_validator.validate_address(
                            address=property_address,
                            municipality=municipality
                        )
                        
                        if result['valid']:
                            st.session_state.address_validated = True
                            st.session_state.address_data = result
                            st.success("✅ Dirección validada")
                            
                            # Show formatted address
                            st.info(f"**Dirección completa:**\n{result['formatted_address']}")
                            
                            # Show coordinates in expander
                            with st.expander("Ver Coordenadas"):
                                st.write(f"**Latitud:** {result['latitude']}")
                                st.write(f"**Longitud:** {result['longitude']}")
                            
                            # Detect regulation automatically
                            regime = detect_regime(municipality)
                            st.session_state.detected_regime = regime
                            
                            st.info(f"""
                            **Régimen Aplicable Detectado:**
                            
                            📋 {regime['type']}: {regime['name']}
                            """)
                            
                        else:
                            st.error(f"❌ {result.get('error', 'Dirección no válida')}")
                            st.session_state.address_validated = False
                    
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")
                        st.info("Asegúrate de tener GOOGLE_MAPS_API_KEY en .env")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.session_state.address_validated = False
        
        # Link to MIPR
        st.markdown("---")
        st.markdown("""
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 3px solid #0284c7;">
            <strong>💡 Consulta el Mapa Oficial:</strong><br>
            <a href="https://gis.jp.pr.gov/mipr/" target="_blank" style="color: #0284c7; text-decoration: none;">
                🗺️ Mapa Interactivo de Puerto Rico (MIPR)
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Optional: Catastro/Finca Number
        catastro_finca = st.text_input(
            "Número de Catastro/Finca (Opcional)",
            placeholder="Ej: 123-456-789",
            help="Número de catastro o finca de la propiedad (opcional)",
            key="catastro_input"
        )
    
    # === RIGHT COLUMN: PROYECTO ===
    with col_right:
        st.markdown("### 🏗️ Paso 2: Proyecto")
        st.markdown("---")
        
        # Distrito de Calificación (Zoning)
        distrito_options = [""] + [
            f"{code} - {data['name']}"
            for code, data in uso_data['distritos'].items()
        ]
        
        distrito_selection = st.selectbox(
            "Distrito de Calificación (Zonificación) *",
            options=distrito_options,
            help="Distrito de zonificación de la propiedad según Tomo 6",
            key="distrito_input"
        )
        
        distrito_code = distrito_selection.split(" - ")[0] if distrito_selection else ""
        
        # Get category based on selected distrito
        selected_category = None
        if distrito_code:
            selected_category = uso_data['distritos'][distrito_code]['category']
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tipo de Proyecto (Main Category)
        tipo_proyecto = st.selectbox(
            "Tipo de Proyecto *",
            options=[""] + list(uso_data['tipos_proyecto'].keys()),
            help="Categoría principal del proyecto",
            key="tipo_proyecto_input"
        )
        
        # Descripción de Uso (Subcategory - based on tipo_proyecto)
        descripcion_uso = None
        if tipo_proyecto:
            subtipos = uso_data['tipos_proyecto'][tipo_proyecto]['subtipos']
            descripcion_uso = st.selectbox(
                "Descripción del Uso *",
                options=[""] + subtipos,
                help="Tipo específico de obra",
                key="descripcion_uso_input"
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Uso Específico (from distrito's usos list)
        uso_especifico = None
        if distrito_code:
            usos_disponibles = uso_data['distritos'][distrito_code]['usos']
            uso_especifico = st.selectbox(
                "Uso Específico Propuesto *",
                options=[""] + usos_disponibles,
                help="Selecciona el uso específico de tu proyecto",
                key="uso_especifico_input"
            )
        
        # Optional: Project description
        with st.expander("Agregar Descripción (Opcional)"):
            project_description = st.text_area(
                "Descripción Adicional",
                placeholder="Ej: Construcción de residencia unifamiliar de 2 niveles...",
                help="Detalles adicionales del proyecto",
                key="description_input"
            )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === VALIDATE BUTTON ===
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        validate_button = st.button(
            "Validar Proyecto Ahora",
            type="primary",
            use_container_width=True,
            key="validate_project_btn"
        )
    
    # === VALIDATION LOGIC ===
    if validate_button:
        # Check required fields
        if not all([
            property_address,
            municipality,
            distrito_code,
            tipo_proyecto,
            descripcion_uso,
            uso_especifico
        ]):
            st.error("Por favor completa todos los campos marcados con *")
        
        elif not st.session_state.get('address_validated', False):
            st.warning("Primero valida la dirección con el botón '🗺️ Validar Dirección'")
        
        else:
            # Run validation
            with st.spinner("Validando proyecto contra Tomo 6..."):
                
                # Create validation context
                validation_context = {
                    'property_address': property_address,
                    'municipality': municipality,
                    'catastro_finca': catastro_finca if catastro_finca else None,
                    'distrito': distrito_code,
                    'tipo_proyecto': tipo_proyecto,
                    'descripcion_uso': descripcion_uso,
                    'uso_especifico': uso_especifico,
                    'regime': st.session_state.get('detected_regime'),
                    'address_data': st.session_state.get('address_data')
                }
                
                # Simple compatibility check
                distrito_data = uso_data['distritos'][distrito_code]
                uso_compatible = uso_especifico in distrito_data['usos']
                
                # Build result
                result = {
                    'viable': uso_compatible,
                    'property_address': property_address,
                    'municipality': municipality,
                    'zoning_district': {
                        'code': distrito_code,
                        'name': distrito_data['name']
                    },
                    'proposed_use': {
                        'code': uso_especifico,
                        'name': uso_especifico,
                        'category': tipo_proyecto
                    },
                    'validation_results': [
                        {
                            'rule_id': 'T6-001',
                            'rule_name': 'Compatibilidad de Uso y Zonificación',
                            'article': 'Reglamento Conjunto, Tomo 6, Artículo 6.1',
                            'passed': uso_compatible,
                            'critical': True,
                            'message': f"El uso '{uso_especifico}' {'ES COMPATIBLE' if uso_compatible else 'NO ES COMPATIBLE'} con el distrito {distrito_code} ({distrito_data['name']})",
                            'details': {
                                'distrito_category': distrito_data['category'],
                                'proyecto_category': tipo_proyecto,
                                'uso_description': descripcion_uso
                            }
                        }
                    ],
                    'summary': _generate_summary(uso_compatible, validation_context),
                    'next_steps': _generate_next_steps(uso_compatible, validation_context),
                    'validated_at': st.session_state.get('address_data', {}).get('formatted_address', property_address),
                    'regime_info': st.session_state.get('detected_regime')
                }
                
                # Add to history
                SessionManager.add_validation_to_history(result)
                
                # Display results inline
                st.markdown("<br><br>", unsafe_allow_html=True)
                render_validation_results(result, uso_compatible)


def _generate_summary(viable: bool, context: dict) -> str:
    """Generate validation summary"""
    if viable:
        return f"""
        ✅ **PROYECTO VIABLE** - El uso '{context['uso_especifico']}' ES COMPATIBLE 
        con el distrito {context['distrito']} según el {context['regime']['type']}.
        
        Tu proyecto de tipo '{context['tipo_proyecto']}' - '{context['descripcion_uso']}' 
        cumple con los requisitos básicos de zonificación del Reglamento Conjunto Tomo 6.
        """
    else:
        return f"""
        ❌ **PROYECTO NO VIABLE** - El uso '{context['uso_especifico']}' NO ES COMPATIBLE 
        con el distrito {context['distrito']}.
        
        Se requieren cambios significativos o solicitud de variación/excepción 
        para proceder con este proyecto.
        """

def _generate_next_steps(viable: bool, context: dict) -> list:
    """Generate recommended next steps"""
    if viable:
        return [
            "1. ✅ Tu proyecto cumple con zonificación básica",
            "2. 📋 Prepara documentos: escritura, certificaciones, planos",
            "3. 👷 Contrata Profesional Autorizado (PA) si aplica",
            "4. 📄 **PRÓXIMO PASO:** Valida documentos completos con nuestra Validación PCOC",
            "5. 📤 Someter solicitud a OGPe o municipio según corresponda"
        ]
    else:
        return [
            "1. 🔄 Solicitar rezoning/cambio de zonificación",
            "2. 📝 Solicitar Consulta de Ubicación (CUB) a Junta de Planificación",
            "3. 🏢 Buscar propiedad en distrito compatible",
            "4. 🔀 Modificar el uso propuesto para cumplir con zonificación",
            "5. ⚖️ Explorar solicitud de variación o excepción (proceso discrecional)"
        ]

def render_validation_results(result: dict, viable: bool):
    """Display validation results inline with prominent upsell"""
    
    st.markdown("""
    <div style="background: #f9fafb; padding: 2rem; border-radius: 16px; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
    """, unsafe_allow_html=True)
    
    st.markdown("## 📊 Resultados de Validación")
    
    # Big result card
    if viable:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                    border: 3px solid #10b981; border-radius: 16px;
                    padding: 2rem; text-align: center; margin: 1.5rem 0;">
            <div style="font-size: 3rem;">✅</div>
            <div style="font-size: 2rem; font-weight: 800; color: #065f46; margin: 0.5rem 0;">
                Proyecto Viable
            </div>
            <div style="font-size: 1.1rem; color: #047857;">
                Tu proyecto cumple con los requisitos básicos de zonificación
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                    border: 3px solid #ef4444; border-radius: 16px;
                    padding: 2rem; text-align: center; margin: 1.5rem 0;">
            <div style="font-size: 3rem;">⚠️</div>
            <div style="font-size: 2rem; font-weight: 800; color: #991b1b; margin: 0.5rem 0;">
                Proyecto No Viable
            </div>
            <div style="font-size: 1.1rem; color: #b91c1c;">
                El uso propuesto no es compatible con la zonificación
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Regime info
    if result.get('regime_info'):
        regime = result['regime_info']
        st.info(f"📋 **Régimen Aplicable:** {regime['type']} - {regime['name']}")
    
    # Summary
    st.markdown("### Resumen")
    st.info(result['summary'])
    
    # Validation details
    st.markdown("### Detalle de Validación")
    for val in result['validation_results']:
        if val['passed']:
            st.markdown(f"""
            <div style="background: #ecfdf5; padding: 1rem; border-left: 4px solid #10b981;
                        border-radius: 8px; margin: 0.5rem 0;">
                <strong style="color: #065f46;">✓ {val['rule_name']}</strong><br>
                <span style="color: #047857;">{val['message']}</span><br>
                <small style="color: #6b7280;">{val['article']}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #fef2f2; padding: 1rem; border-left: 4px solid #ef4444;
                        border-radius: 8px; margin: 0.5rem 0;">
                <strong style="color: #991b1b;">✗ {val['rule_name']}</strong><br>
                <span style="color: #b91c1c;">{val['message']}</span><br>
                <small style="color: #6b7280;">{val['article']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Next steps
    st.markdown("### Próximos Pasos")
    for step in result['next_steps']:
        st.markdown(step)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === PROMINENT UPSELL CTA ===
    if viable:
        st.markdown("<br>", unsafe_allow_html=True)
        render_pcoc_upsell()
    
    # Download report
    st.markdown("---")
    st.markdown("### 📥 Descargar Reporte")
    
    col1, col2 = st.columns(2)
    with col1:
        pdf_bytes = ReportGenerator.generate_pdf(result)
        st.download_button(
            label="📄 Descargar PDF",
            data=pdf_bytes,
            file_name=f"pyxten_validacion_{result['municipality'].replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    
    with col2:
        if st.button("💾 Guardar en Proyecto", use_container_width=True):
            current = SessionManager.get_current_project()
            if current:
                SessionManager.add_report_to_project(current['id'], 'fase1', pdf_bytes)
                st.success(f"✅ Guardado en '{current['name']}'")
            else:
                st.warning("Primero crea un proyecto")

def render_pcoc_upsell():
    """Prominent PCOC validation upsell"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                border-radius: 20px; padding: 3rem; text-align: center;
                box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3); margin: 2rem 0;">
        <div style="font-size: 2.5rem; color: white; font-weight: 800; margin-bottom: 1rem;">
            🚀 ¿Listo para el Siguiente Paso?
        </div>
        <div style="font-size: 1.3rem; color: #dbeafe; margin-bottom: 2rem;">
            Valida TODOS tus documentos antes de someter oficialmente
        </div>
        
        <div style="background: rgba(255,255,255,0.95); border-radius: 16px; 
                    padding: 2rem; margin: 2rem auto; max-width: 600px; text-align: left;">
            <div style="color: #1e40af; font-weight: 700; font-size: 1.2rem; margin-bottom: 1rem; text-align: center;">
                ✨ Validación PCOC Completa Incluye:
            </div>
            <div style="color: #374151; font-size: 1rem; line-height: 1.8;">
                ✅ Análisis automático de planos con IA<br>
                ✅ Verificación de certificaciones y documentos<br>
                ✅ Checklist completo Sección 2.1.9<br>
                ✅ Memorial Explicativo generado<br>
                ✅ Detección de errores antes de someter<br>
                ✅ Reportes PDF profesionales
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🔍 Pre-Verificar Documentos Completos (PCOC)",
            type="primary",
            use_container_width=True,
            key="pcoc_upsell_btn"
        ):
            st.session_state.current_page = 'pcoc_validation'
            st.rerun()