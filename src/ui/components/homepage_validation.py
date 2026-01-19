import streamlit as st
from src.database.rules_loader import RulesDatabase
from src.validators.zoning_validator import ZoningValidator
from src.utils.report_generator import ReportGenerator
from src.services.session_manager import SessionManager
from src.services.district_service import DistrictService
from src.ui.components.gis_map_widget import render_gis_map_link

def render_homepage(rules_db, claude_ai=None, model_router=None):
    """
    Renderiza la pagina principal con el nuevo layout simplificado.
    """
    SessionManager.initialize()
    
    # Header principal - sin emojis
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1.5rem 0;">
        <h1 style="font-size: 2.2rem; font-weight: 800; color: #111827; margin-bottom: 0.5rem;">
            Valida tu Proyecto en Minutos
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Pre-validacion inteligente antes de someter tu solicitud oficial
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs sin emojis
    tab1, tab2 = st.tabs([
        "Validacion Rapida (Zonificacion)",
        "Validacion PCOC Completa"
    ])
    
    with tab1:
        render_phase1_form(rules_db, claude_ai)
    
    with tab2:
        user_plan = st.session_state.get('user_plan', 'professional')
        if user_plan == 'free':
            render_pcoc_upgrade_cta()
        else:
            render_pcoc_quick_access(model_router)


def render_phase1_form(rules_db, claude_ai=None):
    """
    Formulario de validacion Fase 1 con nuevo layout simplificado.
    """

    # Check validation limit
    if not SessionManager.can_validate():
        st.error("""
        ### Has alcanzado el limite de validaciones gratuitas

        Actualiza a Plan Profesional para:
        - Validaciones Fase 1 ilimitadas
        - 10 validaciones PCOC/mes
        - Memorial Explicativo generado con IA
        - Guardar y gestionar proyectos
        """)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Ver Planes y Actualizar", type="primary", use_container_width=True):
                st.session_state.current_page = 'pricing'
                st.rerun()
        return

    # Show remaining validations warning if low
    remaining = SessionManager.get_remaining_validations()
    if remaining <= 2:
        st.warning(f"Te quedan {remaining} validaciones gratuitas este mes")

    # Initialize session state for auto-filled fields
    if 'validated_catastro' not in st.session_state:
        st.session_state.validated_catastro = ""
    if 'validated_zoning_code' not in st.session_state:
        st.session_state.validated_zoning_code = ""
    if 'validated_zoning_name' not in st.session_state:
        st.session_state.validated_zoning_name = ""
    if 'address_validated' not in st.session_state:
        st.session_state.address_validated = False
    if 'validation_warnings' not in st.session_state:
        st.session_state.validation_warnings = []
    if 'validated_coordinates' not in st.session_state:
        st.session_state.validated_coordinates = None

    # Initialize district service
    district_service = DistrictService()

    # ====================
    # GIS MAP LINK SECTION
    # ====================
    render_gis_map_link()

    st.markdown("### Informacion del Proyecto")
    st.markdown("Completa los datos basandote en la calificacion del mapa")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # ROW 1: Describe tu proyecto (full width)
    project_description = st.text_area(
        "Describe tu proyecto",
        placeholder="Describe tu proyecto. Ej: Quiero montar una lavanderia y una oficina en un local comercial...",
        height=100,
        help="Describe el uso que deseas darle a la propiedad. La IA interpretara el tipo de proyecto.",
        key="project_description"
    )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # ROW 2: Direccion (full width)
    property_address = st.text_input(
        "Direccion de la Propiedad *",
        placeholder="Ej: Calle Luna 123, Urb. San Patricio",
        help="Direccion completa de la propiedad",
        key="property_address"
    )

    # ROW 3: Municipio (left) | Catastro (right)
    col1, col2 = st.columns(2)

    with col1:
        municipality = st.selectbox(
            "Municipio *",
            options=["Selecciona un municipio..."] + rules_db.get_municipalities(),
            help="Selecciona el municipio donde se ubica la propiedad",
            key="municipality_select"
        )
        # Clean up selection
        if municipality == "Selecciona un municipio...":
            municipality = ""

    with col2:
        catastro_number = st.text_input(
            "Numero de Catastro (Opcional)",
            value=st.session_state.validated_catastro,
            placeholder="Ej: 123-456-789-01",
            help="Numero de catastro de la propiedad. Puedes encontrarlo en el Mapa MIPR o en tu escritura.",
            key="catastro_input"
        )

    # ====================
    # CALIFICACION SECTION (Manual input with validation)
    # ====================
    st.markdown("#### Calificacion del Predio")
    st.info("""
    **Como encontrar tu calificacion?**
    1. Usa el Mapa MIPR arriba
    2. Busca tu propiedad
    3. Haz clic en el predio
    4. Copia la "Calificacion" (ej: R-2, C-L, etc.)
    """)

    calificacion_input = st.text_input(
        "Calificacion / Zonificacion *",
        placeholder="Ej: R-2, C-L, I-L, etc.",
        help="Calificacion actual del predio segun MIPR",
        key="calificacion_manual"
    )

    # Validate calificacion if entered
    zoning_code = ""
    if calificacion_input and municipality:
        validation_result = district_service.validate_calificacion(calificacion_input, municipality)

        if validation_result['valid']:
            if validation_result['is_pot']:
                st.success(f"{validation_result['message']} - Equivalente RC: {validation_result['rc_equivalent']}")
                zoning_code = validation_result['rc_equivalent']
            else:
                st.info(validation_result['message'])
                zoning_code = validation_result['rc_equivalent']
        else:
            st.warning(validation_result['message'])
    elif calificacion_input and not municipality:
        st.warning("Selecciona un municipio para validar la calificacion")

    # ====================
    # POT-AWARE DISTRICT DROPDOWN
    # ====================
    st.markdown("#### O selecciona de la lista:")

    if municipality:
        districts = district_service.get_districts_for_municipality(municipality)

        # Create dropdown options
        district_options = [""] + [
            f"{d['code']} - {d['name']}"
            for d in districts
        ]

        if district_service.is_pot_municipality(municipality):
            st.caption(f"{municipality} tiene POT propio. Mostrando codigos municipales.")

        district_selection = st.selectbox(
            "Distrito de Zonificacion (alternativa)",
            options=district_options,
            help="Selecciona el distrito de zonificacion si no ingresaste la calificacion manualmente",
            key="district_dropdown"
        )

        # Extract code from dropdown if manual calificacion is empty
        if district_selection and not calificacion_input:
            dropdown_code = district_selection.split(" - ")[0]
            # Get RC equivalent
            zoning_code = district_service.get_rc_equivalent(dropdown_code, municipality)

            # Show RC equivalent if POT
            if district_service.is_pot_municipality(municipality):
                rc_equiv = district_service.get_rc_equivalent(dropdown_code, municipality)
                if rc_equiv != dropdown_code:
                    st.caption(f"Equivalente RC: {rc_equiv}")
    else:
        st.info("Selecciona un municipio primero para ver los distritos disponibles")

    # ====================
    # ADDRESS VALIDATION BUTTON
    # ====================
    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        validate_address_btn = st.button(
            "Validar direccion (opcional)",
            key="validate_address_btn",
            use_container_width=True
        )

    # Handle address validation
    if validate_address_btn:
        if not property_address or not municipality:
            st.error("Por favor ingresa la direccion y selecciona el municipio.")
        else:
            with st.spinner("Validando direccion y consultando servicios GIS..."):
                validate_address_with_gis(property_address, municipality)

    # Show validation warnings if any
    if st.session_state.validation_warnings:
        for warning in st.session_state.validation_warnings:
            st.warning(warning)

    # Show success message if address was validated
    if st.session_state.address_validated:
        st.success("Direccion validada correctamente.")
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    # Main validation button
    validate_project_btn = st.button(
        "Validar Proyecto Ahora",
        type="primary",
        use_container_width=True,
        key="validate_project_btn"
    )
    
    # Handle project validation
    if validate_project_btn:
        # Validate required fields
        if not project_description:
            st.error("Por favor describe tu proyecto.")
            return
        
        if not property_address or not municipality:
            st.error("Por favor ingresa la direccion y selecciona el municipio.")
            return
        
        if not zoning_code:
            st.error("Por favor selecciona o valida el distrito de zonificacion.")
            return
        
        # If address not validated, try to validate it first
        if not st.session_state.address_validated:
            with st.spinner("Validando direccion..."):
                validate_address_with_gis(property_address, municipality)
        
        # Interpret project type using AI if available
        use_code = interpret_project_type(project_description, rules_db, claude_ai)
        
        if not use_code:
            st.error("No se pudo interpretar el tipo de proyecto. Por favor proporciona mas detalles.")
            return
        
        # Run validation
        with st.spinner("Validando proyecto..."):
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
                # Add catastro to result
                result['catastro'] = catastro_number or st.session_state.validated_catastro
                
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


def validate_address_with_gis(address: str, municipality: str):
    """
    Validates address using Google Maps and queries GIS services for catastro/zoning.
    """
    import os
    
    # Reset previous state
    st.session_state.validation_warnings = []
    st.session_state.address_validated = False
    
    # Step 1: Validate address with Google Maps to get coordinates
    coordinates = None
    
    try:
        from src.utils.address_validator import AddressValidator
        
        address_validator = AddressValidator()
        addr_result = address_validator.validate_address(
            address=address,
            municipality=municipality
        )
        
        if addr_result.get('valid'):
            coordinates = (addr_result['latitude'], addr_result['longitude'])
            st.session_state.validated_coordinates = coordinates
            
            if addr_result.get('warning'):
                st.session_state.validation_warnings.append(addr_result['warning'])
        else:
            st.session_state.validation_warnings.append(
                f"Direccion no encontrada: {addr_result.get('error', 'Error desconocido')}. "
                "Puedes ingresar los datos manualmente."
            )
            
    except ValueError as e:
        st.session_state.validation_warnings.append(
            f"Google Maps API no disponible: {str(e)}. Puedes ingresar los datos manualmente."
        )
    except Exception as e:
        st.session_state.validation_warnings.append(
            f"Error validando direccion: {str(e)}. Puedes ingresar los datos manualmente."
        )
    
    # Step 2: If we have coordinates, query GIS services
    if coordinates:
        lat, lng = coordinates
        
        try:
            from src.services.arcgis_pr_client import ArcGISPRClient
            
            gis_client = ArcGISPRClient()
            location_data = gis_client.validate_location(lat, lng)
            
            # Update catastro if found
            if location_data.get('catastro') and location_data['catastro'].get('number'):
                st.session_state.validated_catastro = location_data['catastro']['number']
            else:
                st.session_state.validation_warnings.append(
                    "No se encontro numero de catastro en el sistema CRIM. Puedes ingresarlo manualmente."
                )
            
            # Update zoning if found
            if location_data.get('zoning') and location_data['zoning'].get('code'):
                st.session_state.validated_zoning_code = location_data['zoning']['code']
                st.session_state.validated_zoning_name = location_data['zoning'].get('name', '')
            else:
                st.session_state.validation_warnings.append(
                    "No se encontro calificacion en MIPR. Puedes seleccionarla manualmente."
                )
            
            # Add any GIS warnings
            for warning in location_data.get('warnings', []):
                st.session_state.validation_warnings.append(warning)
            
            # Mark as validated if we got at least some data
            if location_data.get('success'):
                st.session_state.address_validated = True
                
        except ImportError:
            st.session_state.validation_warnings.append(
                "Servicio GIS no disponible. Puedes ingresar los datos manualmente."
            )
        except Exception as e:
            st.session_state.validation_warnings.append(
                f"Error consultando servicios GIS: {str(e)}. Puedes ingresar los datos manualmente."
            )
    
    # If we validated coordinates even without full GIS data, mark as validated
    if coordinates and not st.session_state.address_validated:
        st.session_state.address_validated = True


def interpret_project_type(description: str, rules_db, claude_ai=None) -> str:
    """
    Interprets project description to determine use type code.
    Uses AI if available, falls back to keyword matching.
    """
    description_lower = description.lower()
    
    # Keyword-based mapping for common use types
    keyword_mappings = {
        "RES-SF": ["unifamiliar", "casa", "vivienda", "residencia", "hogar"],
        "RES-MF": ["multifamiliar", "apartamentos", "condominio", "edificio residencial"],
        "COM-OFFICE": ["oficina", "despacho", "consultorio", "profesional"],
        "COM-RETAIL": ["tienda", "comercio", "venta", "retail", "detal", "negocio"],
        "COM-RESTAURANT": ["restaurante", "cafeteria", "comida", "bar", "food"],
        "COM-WAREHOUSE": ["almacen", "bodega", "warehouse", "storage"],
        "IND-LIGHT": ["manufactura", "fabrica", "industrial liviano", "taller"],
        "AGR-FARM": ["finca", "agricola", "cultivo", "siembra", "granja"],
        "MIX-USE": ["mixto", "residencial y comercial", "mixed"]
    }
    
    # Check for lavanderia specifically (common use case)
    if "lavanderia" in description_lower or "laundry" in description_lower:
        # Lavanderia is typically COM-RETAIL or could be COM-OFFICE
        return "COM-RETAIL"
    
    # Try keyword matching first
    for use_code, keywords in keyword_mappings.items():
        for keyword in keywords:
            if keyword in description_lower:
                return use_code
    
    # If AI is available, use it for more sophisticated interpretation
    if claude_ai:
        try:
            # Get all use types for context
            use_types = rules_db.get_use_types()
            use_list = "\n".join([
                f"- {u['code']}: {u['name_es']} - {u.get('description_es', '')}"
                for u in use_types
            ])
            
            prompt = f"""Basandote en la siguiente descripcion de proyecto, determina el codigo de uso mas apropiado.

Descripcion del proyecto:
{description}

Codigos de uso disponibles:
{use_list}

Responde SOLO con el codigo de uso (ej: COM-RETAIL). Sin explicacion."""

            message = claude_ai.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip().upper()
            
            # Validate the response is a valid use code
            valid_codes = [u['code'] for u in use_types]
            if response_text in valid_codes:
                return response_text
                
        except Exception:
            pass
    
    # Default fallback
    return "COM-RETAIL"


def render_pcoc_upgrade_cta():
    """CTA para usuarios free"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 3rem; border-radius: 20px; text-align: center;
                color: white; margin: 2rem 0;">
        <h2>Validacion PCOC - Feature Premium</h2>
        <p style="font-size: 1.2rem; margin: 1.5rem 0;">
            Pre-valida tu permiso de construccion completo antes de someter
        </p>
        
        <div style="background: rgba(255,255,255,0.15); padding: 1.5rem; 
                    border-radius: 12px; margin: 1.5rem 0; text-align: left;">
            <h3 style="color: white;">Incluye:</h3>
            <ul style="font-size: 1.1rem; line-height: 2;">
                <li>Analisis automatico de planos con IA</li>
                <li>Validacion de certificaciones y documentos</li>
                <li>Checklist completo de cumplimiento</li>
                <li>Deteccion de errores antes de someter</li>
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
    """Acceso rapido a PCOC para usuarios premium"""
    
    st.markdown("### Validacion PCOC - Pre-verifica antes de someter")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        used = st.session_state.get('pcoc_validations_used', 0)
        limit = 10
        remaining = max(0, limit - used)
        st.metric("Validaciones Restantes", f"{remaining}/{limit}")
    
    with col2:
        st.metric("Tiempo Promedio", "~12 min")
    
    with col3:
        st.metric("Tasa Exito", "87%")
    
    st.divider()
    
    if st.button(
        "Nueva Validacion PCOC",
        type="primary",
        use_container_width=True
    ):
        st.session_state.current_page = 'pcoc_validation'
        st.rerun()
    
    st.info("""
    **Que validamos?**
    - Planos arquitectonicos (planta, elevaciones, conjunto)
    - Certificaciones (registral, AAA, ambiental)
    - Formularios OGPe
    - Coherencia entre documentos
    - Cumplimiento con Reglamento Conjunto Seccion 2.1.9
    """)


def render_validation_results(result, property_address, municipality):
    """Renderiza los resultados de validacion"""
    
    st.markdown("---")
    st.markdown("## Resultados de Validacion")
    
    # Big viability result
    if result["viable"]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                    border: 3px solid #10b981; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 2rem; font-weight: 800; color: #065f46;">
                PROYECTO VIABLE
            </div>
            <div style="font-size: 1.1rem; color: #047857; margin-top: 0.5rem;">
                Tu proyecto cumple con los requisitos de zonificacion
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                    border: 3px solid #ef4444; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 2rem; font-weight: 800; color: #991b1b;">
                PROYECTO NO VIABLE
            </div>
            <div style="font-size: 1.1rem; color: #b91c1c; margin-top: 0.5rem;">
                Se requieren cambios para cumplir con la zonificacion
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Summary
    st.markdown("### Resumen")
    st.info(result["summary"])
    
    # Show catastro if available
    if result.get('catastro'):
        st.markdown(f"**Numero de Catastro:** {result['catastro']}")
    
    # Detailed validation results
    st.markdown("### Validaciones Detalladas")
    
    for val_result in result["validation_results"]:
        if val_result["passed"]:
            st.markdown(f"""
            <div style="background: #ecfdf5; padding: 1.25rem; border-left: 4px solid #10b981;
                        border-radius: 12px; margin: 1rem 0;">
                <div style="font-weight: 700; color: #065f46; margin-bottom: 0.5rem;">
                    {val_result['rule_name']} - CUMPLE
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
                    {val_result['rule_name']} - NO CUMPLE
                </div>
                <div style="color: #b91c1c;">
                    {val_result['message']}
                </div>
                <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
                    {val_result['article']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Next steps
    st.markdown("### Proximos Pasos Recomendados")
    for i, step in enumerate(result["next_steps"], 1):
        st.markdown(f"**{i}.** {step}")
    
    st.markdown("---")
    
    # Download report section
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
        if st.button("Guardar en Proyecto", use_container_width=True):
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