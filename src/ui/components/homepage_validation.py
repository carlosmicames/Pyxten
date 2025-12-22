import streamlit as st
from src.database.rules_loader import RulesDatabase
from src.validators.zoning_validator import ZoningValidator
from src.utils.report_generator import ReportGenerator
from src.services.session_manager import SessionManager

def render_homepage(rules_db, claude_ai=None, model_router=None):
    """
    Renderiza la página principal.
    Esta es la función principal que organiza los Tabs (Fase 1 vs Fase 2).
    """
    SessionManager.initialize()
    
    # --- HERO SECTION (Header Principal) ---
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #111827; margin-bottom: 0.5rem;">
            Valida tu Proyecto en Minutos
        </h1>
        <p style="font-size: 1.2rem; color: #6b7280;">
            Pre-validación inteligente antes de someter tu solicitud oficial
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- TABS ---
    tab1, tab2 = st.tabs([
        "Validación Rápida (Zonificación)",
        "Validación PCOC Completa"
    ])
    
    # TAB 1: Validación Fase 1 (Formulario)
    with tab1:
        from src.ui.components.phase1_enhanced_wizard import render_enhanced_phase1
        render_enhanced_phase1(rules_db)
    
    # TAB 2: Validación Fase 2 (PCOC / Upsell)
    with tab2:
        # Default to professional for testing - remove paywall
        user_plan = st.session_state.get('user_plan', 'professional')
        
        if user_plan == 'free':
            render_pcoc_upgrade_cta()
        else:
            render_pcoc_quick_access(model_router)
        
def render_phase1_form(rules_db):
    """
    Contiene la lógica del formulario de validación Fase 1.
    Separado de la función principal para evitar bucles infinitos.
    """
    
    # Check if can validate
    if not SessionManager.can_validate():
        st.error("""
        ### Has alcanzado el límite de validaciones gratuitas
        
        Actualiza a Plan Profesional para:
        - ✅ Validaciones Fase 1 ilimitadas
        - ✅ 10 validaciones PCOC/mes
        - ✅ Memorial Explicativo generado con IA
        - ✅ Guardar y gestionar proyectos
        """)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Ver Planes y Actualizar", type="primary", use_container_width=True):
                st.session_state.current_page = 'pricing'
                st.rerun()
        return

    # Show remaining validations warning if low
    remaining = SessionManager.get_remaining_validations()
    if remaining <= 2:
        st.warning(f"Te quedan {remaining} validaciones gratuitas este mes")

    # Main validation form in a clean card
    st.markdown("""
    <div style="background: white; padding: 2.5rem; border-radius: 16px; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); max-width: 900px; margin: 0 auto;">
    """, unsafe_allow_html=True)
    
    st.markdown("### Información del Proyecto")
    st.markdown("Completa los datos para validar tu proyecto contra el Tomo 6")
    
    # Property Address
    property_address = st.text_input(
        "Dirección de la Propiedad *",
        placeholder="Ej: Calle Luna 123, Urb. San Patricio",
        help="Dirección completa de la propiedad",
        key="prop_address"
    )
    
    # Two columns for Municipality and Zoning
    col1, col2 = st.columns(2)
    
    with col1:
        municipality = st.selectbox(
            "Municipio *",
            options=[""] + rules_db.get_municipalities(),
            help="Selecciona el municipio donde se ubica la propiedad",
            index=0
        )
    
    with col2:
        zoning_options = [""] + [
            f"{d['code']} - {d['name_es']}"
            for d in rules_db.get_zoning_districts()
        ]
        
        zoning_selection = st.selectbox(
            "Distrito de Zonificación *",
            options=zoning_options,
            help="Distrito de zonificación de la propiedad",
            index=0
        )
        
        zoning_code = zoning_selection.split(" - ")[0] if zoning_selection else ""
    
    # Proposed Use
    use_options = [""] + [
        f"{u['code']} - {u['name_es']}"
        for u in rules_db.get_use_types()
    ]
    
    use_selection = st.selectbox(
        "Uso Propuesto *",
        options=use_options,
        help="Tipo de uso que deseas construir",
        index=0
    )
    
    use_code = use_selection.split(" - ")[0] if use_selection else ""
    
    # Optional project description
    with st.expander("Agregar Descripción (Opcional)"):
        project_description = st.text_area(
            "Descripción del Proyecto",
            placeholder="Ej: Construcción de residencia unifamiliar de 2 niveles con piscina...",
            help="Detalles adicionales que ayuden a entender el proyecto",
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Validate button (prominent)
    validate_button = st.button(
        "Validar Proyecto Ahora",
        use_container_width=True,
        type="primary"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Validation logic
    if validate_button:
        if not all([property_address, municipality, zoning_code, use_code]):
            st.error("Por favor completa todos los campos marcados con *")
        else:
            with st.spinner("Validando proyecto"):
                validator = ZoningValidator(rules_db)
                
                result = validator.validate_project(
                    property_address=property_address,
                    municipality=municipality,
                    zoning_code=zoning_code,
                    proposed_use_code=use_code
                )
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    # Add to history
                    SessionManager.add_validation_to_history(result)
                    
                    # Add to current project if exists
                    current_project = SessionManager.get_current_project()
                    if current_project:
                        SessionManager.update_project(
                            current_project['id'],
                            {
                                'phase1_completed': True,
                                'phase1_result': result
                            }
                        )
                    
                    # Show results
                    render_validation_results(result, property_address, municipality)

def render_pcoc_upgrade_cta():
    """CTA para usuarios free"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 3rem; border-radius: 20px; text-align: center;
                color: white; margin: 2rem 0;">
        <h2>Validación PCOC - Feature Premium</h2>
        <p style="font-size: 1.2rem; margin: 1.5rem 0;">
            Pre-valida tu permiso de construcción completo antes de someter
        </p>
        
        <div style="background: rgba(255,255,255,0.15); padding: 1.5rem; 
                    border-radius: 12px; margin: 1.5rem 0; text-align: left;">
            <h3 style="color: white;">✨ Incluye:</h3>
            <ul style="font-size: 1.1rem; line-height: 2;">
                <li>Análisis automático de planos con IA</li>
                <li>Validación de certificaciones y documentos</li>
                <li>Checklist completo de cumplimiento</li>
                <li>Detección de errores antes de someter</li>
                <li>Reportes PDF profesionales</li>
                <li>10 validaciones PCOC/mes</li>
            </ul>
        </div>
        
        <p style="font-size: 1.3rem; font-weight: 600; margin: 1.5rem 0;">
            Solo $99/mes - Ahorra tiempo y rechazos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Ver Planes y Actualizar", type="primary", use_container_width=True):
            st.session_state.current_page = 'pricing'
            st.rerun()

def render_pcoc_quick_access(model_router):
    """Acceso rápido a PCOC para usuarios premium"""
    
    st.markdown("### 🏗️ Validación PCOC - Pre-verifica antes de someter")
    
    # Stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        used = st.session_state.get('pcoc_validations_used', 0)
        limit = 10  # Plan profesional
        remaining = max(0, limit - used)
        st.metric("Validaciones Restantes", f"{remaining}/{limit}")
    
    with col2:
        st.metric("Tiempo Promedio", "~12 min")
    
    with col3:
        st.metric("Tasa Éxito", "87%")
    
    st.divider()
    
    # CTA principal
    if st.button(
        "➕ Nueva Validación PCOC",
        type="primary",
        use_container_width=True
    ):
        st.session_state.current_page = 'pcoc_validation'
        st.rerun()
    
    # Info adicional
    st.info("""
    **¿Qué validamos?**
    - ✅ Planos arquitectónicos (planta, elevaciones, conjunto)
    - ✅ Certificaciones (registral, AAA, ambiental)
    - ✅ Formularios OGPe
    - ✅ Coherencia entre documentos
    - ✅ Cumplimiento con Reglamento Conjunto Sección 2.1.9
    """)

def render_validation_results(result, property_address, municipality):
    """Renderiza los resultados de validación con CTA prominente"""
    
    st.markdown("""
    <div style="background: #f9fafb; padding: 2rem; border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-top: 2rem;">
    """, unsafe_allow_html=True)
    
    st.markdown("## Resultados de Validación")
    
    # Big viability result
    if result["viable"]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                    border: 3px solid #10b981; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;
                    animation: slideIn 0.6s ease;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;"></div>
            <div style="font-size: 2rem; font-weight: 800; color: #065f46;">
                Tu proyecto cumple con los requisitos basicos del Reglamento Conjunto
            </div>
            <div style="font-size: 1.1rem; color: #047857; margin-top: 0.5rem;">
                Tu proyecto cumple con los requisitos de zonificación
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                    border: 3px solid #ef4444; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;
                    animation: slideIn 0.6s ease;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-size: 2rem; font-weight: 800; color: #991b1b;">
                Proyecto no cumple con los requisitos basicos del Reglamento Conjunto
            </div>
            <div style="font-size: 1.1rem; color: #b91c1c; margin-top: 0.5rem;">
                Se requieren cambios para cumplir con la zonificación
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Summary
    st.markdown("### Resumen")
    st.info(result["summary"])
    
    # Detailed validation results
    st.markdown("### Validaciones Detalladas")
    
    for val_result in result["validation_results"]:
        if val_result["passed"]:
            st.markdown(f"""
            <div style="background: #ecfdf5; padding: 1.25rem; border-left: 4px solid #10b981;
                        border-radius: 12px; margin: 1rem 0;">
                <div style="font-weight: 700; color: #065f46; margin-bottom: 0.5rem;">
                    ✓ {val_result['rule_name']}
                </div>
                <div style="color: #047857;">
                    {val_result['message']}
                </div>
                <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
                    {val_result['article']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #fef2f2; padding: 1.25rem; border-left: 4px solid #ef4444;
                        border-radius: 12px; margin: 1rem 0;">
                <div style="font-weight: 700; color: #991b1b; margin-bottom: 0.5rem;">
                    ✗ {val_result['rule_name']}
                </div>
                <div style="color: #b91c1c;">
                    {val_result['message']}
                </div>
                <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
                    📄 {val_result['article']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Next steps
    st.markdown("### Próximos Pasos Recomendados")
    for i, step in enumerate(result["next_steps"], 1):
        st.markdown(f"**{i}.** {step}")
    
    st.markdown("---")
    
    # CALL TO ACTION - Prominent and eye-catching
    if result["viable"]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    border-radius: 20px; padding: 3rem; text-align: center;
                    margin: 2rem 0; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
                    animation: pulse 2s infinite;">
            <div style="font-size: 2rem; font-weight: 800; color: white; margin-bottom: 1rem;">
                🚀 ¿Listo para el Siguiente Paso?
            </div>
            <div style="font-size: 1.2rem; color: #dbeafe; margin-bottom: 2rem;">
                Pre-verifica TODOS tus documentos con nuestra validación completa PCOC
            </div>
            <div style="background: white; border-radius: 12px; padding: 1.5rem; margin: 1.5rem auto; max-width: 500px;">
                <div style="color: #1e40af; font-weight: 600; margin-bottom: 1rem;">
                    ✨ Validación PCOC incluye:
                </div>
                <div style="text-align: left; color: #374151; font-size: 0.95rem;">
                    ✓ Análisis de planos arquitectónicos con IA<br>
                    ✓ Verificación de certificaciones<br>
                    ✓ Checklist completo de cumplimiento<br>
                    ✓ Memorial Explicativo generado<br>
                    ✓ Detección automática de errores
                </div>
            </div>
        </div>
        
        <style>
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Pre-Verificar Solicitud PCOC (Próximamente)",
                type="primary",
                use_container_width=True
            ):
                st.info("""
                ** Fase 2 en Desarrollo**
                
                La validación completa PCOC estará disponible próximamente.
                
                **Incluirá:**
                - Análisis inteligente de documentos
                - Verificación de cumplimiento total
                - Memorial explicativo generado
                - Detección de errores comunes
                
                **¿Interesado en acceso anticipado?**
                Contáctanos: info@pyxten.com | (787) 506-0402
                """)
    
    # Download report section
    st.markdown("---")
    st.markdown("### Descargar Reporte")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pdf_bytes = ReportGenerator.generate_pdf(result)
        st.download_button(
            label="Descargar Reporte PDF",
            data=pdf_bytes,
            file_name=f"pyxten_validacion_{municipality.replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    
    with col2:
        if st.button("💾 Guardar en Proyecto", use_container_width=True):
            current_project = SessionManager.get_current_project()
            if current_project:
                SessionManager.add_report_to_project(
                    current_project['id'],
                    'fase1',
                    pdf_bytes
                )
                st.success(f"Reporte guardado en '{current_project['name']}'")
            else:
                st.warning("Primero crea un proyecto para guardar el reporte")
                if st.button("Crear Proyecto", key="create_proj_cta"):
                    st.session_state.current_page = 'new_project'
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)