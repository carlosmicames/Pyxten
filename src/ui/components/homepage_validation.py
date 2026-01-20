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
    if 'validated_coordinates' not in st.session_state:
        st.session_state.validated_coordinates = None
    if 'catastro_number' not in st.session_state:
        st.session_state.catastro_number = ""
    if 'address_validated' not in st.session_state:
        st.session_state.address_validated = False
    if 'validation_warnings' not in st.session_state:
        st.session_state.validation_warnings = []

    # Initialize district service
    district_service = DistrictService()

    # ====================
    # INFORMACION DEL PROYECTO
    # ====================
    st.markdown("### Informacion del Proyecto")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # ====================
    # 1. DESCRIPCION DEL PROYECTO (PRIMERO)
    # ====================
    st.markdown("#### Describe tu Proyecto")
    
    property_description = st.text_area(
        "Que tipo de uso o construccion deseas?",
        placeholder="Ejemplos:\n"
                   "- 'Quiero construir una residencia unifamiliar'\n",
        height=30,  # FIXED: Reduced from 60 to 30
        help="Describe tu proyecto de forma natural - el sistema lo interpretara automaticamente",
        key="project_description"
    )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # ====================
    # 2. DIRECCION Y MUNICIPIO
    # ====================
    col1, col2 = st.columns(2)

    with col1:
        property_address = st.text_input(
            "Direccion de la Propiedad *",
            placeholder="Ej: Calle Luna 123, Urb. San Patricio",
            help="Direccion completa de la propiedad",
            key="property_address"
        )

    with col2:
        municipality = st.selectbox(
            "Municipio *",
            options=["Selecciona un municipio..."] + rules_db.get_municipalities(),
            help="Selecciona el municipio donde se ubica la propiedad",
            key="municipality_select"
        )
        # Clean up selection
        if municipality == "Selecciona un municipio...":
            municipality = ""

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # ====================
    # 3. BOTON VALIDAR DIRECCION
    # ====================
    validate_address_btn = st.button(
        "Validar direccion",
        key="validate_address_btn",
        use_container_width=False
    )

    # Handle address validation
    if validate_address_btn:
        if not property_address or not municipality:
            st.error("Por favor ingresa la direccion y selecciona el municipio.")
        else:
            with st.spinner("Validando direccion..."):
                validate_address_with_gis(property_address, municipality)

    # Show validation warnings if any
    if st.session_state.validation_warnings:
        for warning in st.session_state.validation_warnings:
            st.warning(warning)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # ====================
    # 4. COORDENADAS Y CATASTRO (MISMO ROW)
    # ====================
    if st.session_state.validated_coordinates:
        lat, lng = st.session_state.validated_coordinates
        
        st.success("Direccion validada correctamente")
        
        # Row con Coordenadas y Catastro
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input(
                "Coordenadas (Latitud, Longitud)",
                value=f"{lat:.6f}, {lng:.6f}",
                disabled=True,
                help="Usa estas coordenadas para buscar tu propiedad en el mapa MIPR"
            )
        
        with col2:
            # FIXED: Auto-fill catastro from session state
            catastro_value = st.session_state.get('catastro_number', '')
            if catastro_value == "No disponible":
                catastro_value = ""  # Clear the "No disponible" text for user input
            
            catastro_number = st.text_input(
                "Catastro",
                value=catastro_value,
                placeholder="Ej: 123-456-789-01" if not catastro_value else "",
                help="Numero de catastro auto-detectado. Puedes editarlo si es incorrecto.",
                key="catastro_input"
            )
            
            # Show caveat if catastro was auto-filled
            if st.session_state.get('catastro_number') and st.session_state.catastro_number != "No disponible":
                st.caption("⚠️ Debe verificar esta información para confirmar su exactitud.")
        
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        
        # Boton de abrir mapa
        mipr_url = f"https://gis.jp.pr.gov/mipr/?center={lng},{lat}&zoom=18"
        
        st.markdown(f"""
        <a href="{mipr_url}" target="_blank" style="text-decoration: none;">
            <button style="
                background-color: #0ea5e9;
                color: white;
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 0.375rem;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin-bottom: 1rem;
            ">
                Abrir mapa de calificaciones
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        # Instrucciones
        with st.expander("Instrucciones - Como usar las coordenadas en el mapa"):
            st.markdown(f"""
            **Sigue estos pasos para identificar tu calificacion:**
            
            1. **Haz clic** en el boton "Abrir mapa de calificaciones" arriba
            2. El mapa se abrira centrado en tu propiedad usando las coordenadas:
               - **Latitud:** {lat:.6f}
               - **Longitud:** {lng:.6f}
            3. **Identifica tu predio** en el mapa (deberia estar en el centro)
            4. **Haz clic** sobre el predio para ver la informacion
            5. **Copia la "Calificacion"** que aparece (ejemplo: R-2, C-L, RU-1, etc.)
            6. **Selecciona la calificacion** en el dropdown de abajo
            
            **Tip:** Si el mapa no esta centrado exactamente en tu propiedad, usa las coordenadas
            para buscar manualmente en la barra de busqueda del mapa MIPR.
            """)
    else:
        # Si no se ha validado, no mostrar el campo de catastro
        catastro_number = None

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # ====================
    # 5. CALIFICACION/DISTRITO (DROPDOWN CONSOLIDADO)
    # ====================
    st.markdown("#### Calificacion del Predio")
    
    zoning_code = ""
    
    if municipality:
        districts = district_service.get_districts_for_municipality(municipality)

        # Create consolidated dropdown options - ELIMINAR DUPLICADOS
        seen_codes = set()
        calificacion_options = ["Selecciona una calificacion..."]

        for d in districts:
            code = d['code']
            # Solo agregar si no lo hemos visto antes
            if code not in seen_codes:
                seen_codes.add(code)
                # Formato: Solo el codigo (sin descripcion)
                calificacion_options.append(code)

        # Info sobre POT si aplica
        if district_service.is_pot_municipality(municipality):
            st.caption(f"Nota: {municipality} tiene POT propio. Se mostrara el equivalente RC automaticamente.")

        calificacion_selection = st.selectbox(
            "Calificacion / Distrito de Zonificacion *",
            options=calificacion_options,
            help="Selecciona la calificacion del predio segun aparece en el mapa MIPR",
            key="calificacion_distrito_dropdown"
        )

        # Extract code and get RC equivalents
        if calificacion_selection and calificacion_selection != "Selecciona una calificacion...":
            selected_code = calificacion_selection

            # Get all RC equivalents
            rc_equivalents = district_service.get_rc_equivalents(selected_code, municipality)

            # Use first equivalent for backwards compatibility
            zoning_code = rc_equivalents[0] if rc_equivalents else selected_code

            # Store equivalents in session state for validation
            st.session_state.rc_equivalents = rc_equivalents

            # Show RC equivalents if POT and different from original code
            if district_service.is_pot_municipality(municipality):
                if rc_equivalents and rc_equivalents[0] != selected_code:
                    if len(rc_equivalents) > 1:
                        st.info(f"Codigo POT '{selected_code}' equivale a RC: {', '.join(rc_equivalents)}")
                    else:
                        st.info(f"Codigo POT '{selected_code}' equivale a RC: {rc_equivalents[0]}")
    else:
        st.info("Selecciona un municipio primero para ver las calificaciones disponibles")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    # ====================
    # 6. BOTON DE VALIDAR PROYECTO
    # ====================
    validate_project_btn = st.button(
        "Validar Proyecto Ahora",
        type="primary",
        use_container_width=True,
        key="validate_project_btn"
    )
    
    # Handle project validation
    if validate_project_btn:
        # Validate required fields
        if not property_description:
            st.error("Por favor describe tu proyecto.")
            return
        
        if not property_address or not municipality:
            st.error("Por favor ingresa la direccion y selecciona el municipio.")
            return
        
        if not zoning_code:
            st.error("Por favor selecciona la calificacion/distrito de zonificacion.")
            return
        
        # Interpret project type using AI if available
        use_code = interpret_project_type(property_description, rules_db, claude_ai)
        
        if not use_code:
            st.error("No se pudo interpretar el tipo de proyecto. Por favor proporciona mas detalles.")
            return
        
        # Run validation
        with st.spinner("Validando proyecto..."):
            validator = ZoningValidator(rules_db)

            # Get RC equivalents from session state or use zoning_code
            rc_equivalents = st.session_state.get('rc_equivalents', [zoning_code])

            result = validator.validate_project(
                property_address=property_address,
                municipality=municipality,
                zoning_code=zoning_code,
                proposed_use_code=use_code,
                rc_equivalents=rc_equivalents
            )
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                # FIXED: Add catastro to result for DISPLAY only (not PDF)
                # Store catastro separately for UI display
                display_catastro = catastro_number if catastro_number else st.session_state.get('catastro_number', 'No disponible')
                
                # Add metadata to result
                result['property_address'] = property_address
                result['municipality'] = municipality
                result['project_description'] = property_description
                
                # Store PDF data separately
                pdf_bytes = ReportGenerator.generate_pdf(result)
                st.session_state.validation_pdf_data = pdf_bytes
                
                # Add to history with description and PDF
                history_entry = result.copy()
                history_entry['project_description'] = property_description
                history_entry['pdf_data'] = pdf_bytes
                SessionManager.add_validation_to_history(history_entry)
                
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
                
                # Show results with catastro for display
                render_validation_results(result, property_address, municipality, display_catastro)


def validate_address_with_gis(address: str, municipality: str):
    """
    Validates address using Google Maps to get coordinates.
    Then fetches catastro number from ArcGIS/CRIM.
    """
    import os
    
    # Reset previous state
    st.session_state.validation_warnings = []
    st.session_state.address_validated = False
    st.session_state.catastro_number = ""
    
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
            st.session_state.address_validated = True
            
            if addr_result.get('warning'):
                st.session_state.validation_warnings.append(addr_result['warning'])
        else:
            st.session_state.validation_warnings.append(
                f"Direccion no encontrada: {addr_result.get('error', 'Error desconocido')}."
            )
            
    except ValueError as e:
        st.session_state.validation_warnings.append(
            f"Google Maps API no disponible: {str(e)}."
        )
    except Exception as e:
        st.session_state.validation_warnings.append(
            f"Error validando direccion: {str(e)}."
        )

    # Step 2: Fetch catastro number from CRIM if coordinates available
    if coordinates:
        try:
            from src.services.arcgis_pr_client import ArcGISPRClient
            
            arcgis_client = ArcGISPRClient()
            parcel_result = arcgis_client.get_parcel_info(coordinates[0], coordinates[1])
            
            if parcel_result.get('success') and parcel_result.get('catastro'):
                st.session_state.catastro_number = parcel_result['catastro']
                st.success(f"✅ Número de catastro detectado: {parcel_result['catastro']}")
            else:
                st.session_state.catastro_number = "No disponible"
                st.info("ℹ️ No se pudo obtener el número de catastro automáticamente. Puedes ingresarlo manualmente.")
                
        except Exception as e:
            st.session_state.catastro_number = "No disponible"
            st.session_state.validation_warnings.append(
                f"No se pudo obtener número de catastro: {str(e)}"
            )
    else:
        st.session_state.catastro_number = "No disponible"


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
            
            response = claude_ai.generate(prompt, max_tokens=50)
            use_code = response.strip()
            
            # Validate that it's a real code
            valid_codes = [u['code'] for u in use_types]
            if use_code in valid_codes:
                return use_code
                
        except Exception as e:
            st.warning(f"Error usando IA para interpretar proyecto: {str(e)}")
    
    # Default fallback
    return "COM-RETAIL"


def render_pcoc_upgrade_cta():
    """Renders upgrade CTA for PCOC validation"""
    st.info("""
    ### Validacion PCOC Completa

    Esta funcionalidad esta disponible en el Plan Profesional.

    **Incluye:**
    - Validacion completa de documentos PCOC
    - Planos arquitectonicos (planta, elevaciones, conjunto)
    - Certificaciones (registral, AAA, ambiental)
    - Formularios OGPe
    - Coherencia entre documentos
    - Cumplimiento con Reglamento Conjunto Seccion 2.1.9
    """)


def render_pcoc_quick_access(model_router):
    """Quick access to PCOC validation for professional users"""
    st.info("""
    ### Validacion PCOC Completa (Proximamente)

    **Validacion completa incluye:**
    - Planos arquitectonicos (planta, elevaciones, conjunto)
    - Certificaciones (registral, AAA, ambiental)
    - Formularios OGPe
    - Coherencia entre documentos
    - Cumplimiento con Reglamento Conjunto Seccion 2.1.9
    """)


def render_validation_results(result, property_address, municipality, catastro_display):
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

    # FIXED: Show catastro in UI with caveat (NOT in PDF)
    if catastro_display and catastro_display != "No disponible":
        st.markdown(f"""
        <div style="background: #f3f4f6; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">
                📍 Número de Catastro
            </div>
            <div style="font-size: 1.1rem; color: #10b981; font-weight: 700;">
                {catastro_display}
            </div>
            <div style="font-size: 0.85rem; color: #ef4444; margin-top: 0.5rem;">
                ⚠️ Debe verificar esta información para confirmar su exactitud.
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif catastro_display == "No disponible":
        st.markdown("""
        <div style="background: #fef2f2; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <div style="font-weight: 600; color: #991b1b;">
                📍 Número de Catastro: No disponible
            </div>
            <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
                No se pudo obtener el número de catastro para esta ubicación.
            </div>
        </div>
        """, unsafe_allow_html=True)

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

    st.markdown("---")

    # Download report section
    st.markdown("### Descargar Reporte")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # FIXED: PDF already generated and stored in session
        pdf_bytes = st.session_state.get('validation_pdf_data')
        if pdf_bytes:
            st.download_button(
                label="📥 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"pyxten_validacion_{municipality.replace(' ', '_').lower()}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_results"
            )
        else:
            st.error("Error generando PDF")
    
    with col2:
        if st.button("Guardar en Proyecto", use_container_width=True):
            st.session_state.show_save_modal = True
            st.session_state.validation_to_save = {
                'result': result,
                'pdf': st.session_state.validation_pdf_data,
                'address': property_address,
                'municipality': municipality
            }
            st.rerun()

    # Save modal
    if st.session_state.get('show_save_modal'):
        render_save_modal()


def render_save_modal():
    """Render modal to save validation to a project folder"""
    st.markdown("### Guardar validacion en proyecto")

    # Get user's folders/projects
    projects = SessionManager.get_all_projects()

    tab1, tab2 = st.tabs(["Carpeta existente", "Nueva carpeta"])

    with tab1:
        if not projects:
            st.info("No tienes carpetas de proyecto. Crea una en la pestana 'Nueva carpeta'.")
        else:
            project_options = {p['name']: p['id'] for p in projects.values()}
            selected_project = st.selectbox(
                "Selecciona carpeta",
                options=list(project_options.keys()),
                key="select_existing_folder"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Guardar aqui", type="primary", use_container_width=True, key="save_to_existing"):
                    if selected_project:
                        project_id = project_options[selected_project]
                        validation_data = st.session_state.validation_to_save

                        # Add report to project
                        SessionManager.add_report_to_project(
                            project_id,
                            'fase1',
                            validation_data['pdf']
                        )

                        # Update project with validation result
                        SessionManager.update_project(project_id, {
                            'phase1_completed': True,
                            'phase1_result': validation_data['result']
                        })

                        st.success(f"Validacion guardada en '{selected_project}'")
                        st.session_state.show_save_modal = False
                        st.rerun()

            with col2:
                if st.button("Cancelar", use_container_width=True, key="cancel_save_existing"):
                    st.session_state.show_save_modal = False
                    st.rerun()

    with tab2:
        new_folder_name = st.text_input(
            "Nombre de la nueva carpeta",
            placeholder="Ej: Cliente XYZ - Residencial",
            key="new_folder_name_input"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Crear y Guardar", type="primary", use_container_width=True, key="create_and_save"):
                if new_folder_name:
                    validation_data = st.session_state.validation_to_save

                    # Create new project/folder
                    project_id = SessionManager.create_project(
                        name=new_folder_name,
                        address=validation_data['address'],
                        municipality=validation_data['municipality']
                    )

                    # Add report to project
                    SessionManager.add_report_to_project(
                        project_id,
                        'fase1',
                        validation_data['pdf']
                    )

                    # Update project with validation result
                    SessionManager.update_project(project_id, {
                        'phase1_completed': True,
                        'phase1_result': validation_data['result']
                    })

                    st.success(f"Carpeta '{new_folder_name}' creada y validacion guardada")
                    st.session_state.show_save_modal = False
                    st.rerun()
                else:
                    st.error("Por favor ingresa un nombre para la carpeta")

        with col2:
            if st.button("Cancelar", use_container_width=True, key="cancel_save_new"):
                st.session_state.show_save_modal = False
                st.rerun()