"""
Enhanced Phase 1 Validation Wizard
4-step process with improved UX and preliminary compatibility analysis
"""

import streamlit as st
from src.database.rules_loader import RulesDatabase
from src.utils.address_validator import AddressValidator
from src.services.session_manager import SessionManager
from typing import Dict, Optional
import json

# Lista de municipios con POT vigente
MUNICIPIOS_POT = [
    "Barceloneta", "Caguas", "Carolina", "Corozal", "Culebra",
    "Guaynabo", "Juncos", "Lajas", "Mayagüez", "Ponce",
    "Rincón", "San Juan", "Santa Isabel", "Vieques"
]

# Mapeo de tipos de proyecto a categorías de distrito
PROYECTO_DISTRITO_MAP = {
    "Residencial": ["residential", "mixed"],
    "Comercial": ["commercial", "mixed"],
    "Industrial": ["industrial"],
    "Turístico": ["tourist", "commercial"],
    "Agrícola/Rural": ["agricultural", "rural"],
    "Dotacional/Conservación": ["institutional", "conservation"],
    "Histórico/Especial": ["conservation", "residential", "commercial"]
}


class EnhancedPhase1Wizard:
    """Enhanced Phase 1 validation wizard with 4 steps"""
    
    def __init__(self, rules_db: RulesDatabase):
        self.rules_db = rules_db
        
        # Initialize wizard state
        if 'phase1_step' not in st.session_state:
            st.session_state.phase1_step = 0
        
        if 'phase1_data' not in st.session_state:
            st.session_state.phase1_data = {}
        
        if 'phase1_result' not in st.session_state:
            st.session_state.phase1_result = None
    
    def render(self):
        """Main render method"""
        
        # Progress indicator
        self._render_progress()
        
        # Render current step
        if st.session_state.phase1_step == 0:
            self._render_step1_location()
        elif st.session_state.phase1_step == 1:
            self._render_step2_project_type()
        elif st.session_state.phase1_step == 2:
            self._render_step3_results()
        elif st.session_state.phase1_step == 3:
            self._render_step4_upsell()
    
    def _render_progress(self):
        """Progress indicator"""
        steps = ["Ubicación", "Proyecto", "Resultado", "Validación Completa"]
        current = st.session_state.phase1_step
        
        cols = st.columns(len(steps))
        for i, step in enumerate(steps):
            with cols[i]:
                if i < current:
                    st.markdown(f"✅ **{step}**")
                elif i == current:
                    st.markdown(f"🔵 **{step}**")
                else:
                    st.markdown(f"⚪ {step}")
        
        st.markdown("---")
    
    def _render_step1_location(self):
        """Step 1: Location with Google Maps validation"""
        
        st.markdown("### Paso 1: Ubicación de la Propiedad")
        st.info("Verificaremos tu dirección con Google Maps para asegurar precisión")
        
        # Address input
        address = st.text_input(
            "Dirección de la Propiedad *",
            value=st.session_state.phase1_data.get('address', ''),
            placeholder="Ej: Calle Luna 123, San Juan",
            help="Dirección física completa de la propiedad"
        )
        
        # Validate address button
        if st.button("Validar Dirección con Google Maps", use_container_width=True):
            if not address:
                st.error("Por favor ingresa una dirección")
            else:
                with st.spinner("Validando dirección..."):
                    try:
                        validator = AddressValidator()
                        
                        # Try without municipality first
                        result = validator.validate_address(
                            address=address,
                            municipality="",  # Let Google figure it out
                            country="Puerto Rico"
                        )
                        
                        if result['valid']:
                            st.success("✅ Dirección válida")
                            
                            # Extract municipality from components
                            municipality = result.get('components', {}).get('city', '')
                            
                            # Store validated data
                            st.session_state.phase1_data.update({
                                'address': address,
                                'formatted_address': result['formatted_address'],
                                'municipality': municipality,
                                'latitude': result['latitude'],
                                'longitude': result['longitude'],
                                'address_validated': True
                            })
                            
                            # Show formatted address
                            st.info(f"**Dirección completa:** {result['formatted_address']}")
                            
                            # Show municipality (auto-detected)
                            st.success(f"**Municipio detectado:** {municipality}")
                            
                            # Expandable map preview
                            with st.expander("Ver en Mapa"):
                                st.map(
                                    data=[[result['latitude'], result['longitude']]],
                                    zoom=15
                                )
                                st.caption(f"Coordenadas: {result['latitude']}, {result['longitude']}")
                        
                        else:
                            st.error(f"❌ No se pudo validar la dirección: {result.get('error', 'Error desconocido')}")
                            st.warning("Verifica la dirección e intenta nuevamente")
                    
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")
                        st.info("Asegúrate de tener GOOGLE_MAPS_API_KEY configurada en .env")
                    except Exception as e:
                        st.error(f"Error validando dirección: {str(e)}")
        
        # Show validated data if available
        if st.session_state.phase1_data.get('address_validated'):
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Dirección Validada:**")
                st.write(st.session_state.phase1_data['formatted_address'])
            
            with col2:
                st.markdown("**Municipio:**")
                st.write(st.session_state.phase1_data['municipality'])
            
            # Optional: Catastro/Finca number
            st.markdown("---")
            catastro = st.text_input(
                "Número de Catastro/Finca (Opcional)",
                value=st.session_state.phase1_data.get('catastro', ''),
                placeholder="Ej: 123-456-789",
                help="Si lo conoces, facilita la verificación posterior. Será validado contra el Mapa Interactivo de PR en Fase 2."
            )
            
            if catastro:
                st.session_state.phase1_data['catastro'] = catastro
            
            # Detect applicable regime
            municipality = st.session_state.phase1_data['municipality']
            regime = self._detect_regime(municipality)
            
            st.markdown("---")
            st.markdown("**📋 Régimen Aplicable Detectado:**")
            
            if regime == "POT":
                st.info(f"""
                **Plan de Ordenación Territorial (POT) Municipal**
                
                El municipio de **{municipality}** cuenta con POT vigente. 
                La nomenclatura de distritos está armonizada con el Reglamento Conjunto 2023.
                """)
            else:
                st.info(f"""
                **Reglamento Conjunto 2023**
                
                El municipio de **{municipality}** aplica el Reglamento Conjunto como régimen principal.
                Los distritos están según Tabla 6.1 - Equivalencias Distritos de Calificación.
                """)
            
            st.session_state.phase1_data['regime'] = regime
            
            # Navigation
            st.markdown("---")
            if st.button("Siguiente: Tipo de Proyecto →", type="primary", use_container_width=True):
                st.session_state.phase1_step = 1
                st.rerun()
        
        else:
            st.warning("Valida tu dirección con Google Maps para continuar")
    
    def _render_step2_project_type(self):
        """Step 2: Project type and description"""
        
        st.markdown("### Paso 2: Tipo de Proyecto")
        
        # Show validated location summary
        with st.expander("Ubicación Validada", expanded=False):
            st.write(f"**Dirección:** {st.session_state.phase1_data['formatted_address']}")
            st.write(f"**Municipio:** {st.session_state.phase1_data['municipality']}")
            st.write(f"**Régimen:** {st.session_state.phase1_data['regime']}")
        
        st.markdown("---")
        
        # Project type selection
        project_type = st.selectbox(
            "Tipo de Proyecto *",
            options=[
                "",
                "Residencial",
                "Comercial",
                "Industrial",
                "Turístico",
                "Agrícola/Rural",
                "Dotacional/Conservación",
                "Histórico/Especial"
            ],
            help="Categoría general del proyecto propuesto"
        )
        
        # Project description
        project_description = st.selectbox(
            "Descripción del Uso Propuesto *",
            options=[
                "",
                "Nueva Construcción",
                "Remodelación",
                "Cambio de Uso",
                "Ampliación"
            ],
            help="Tipo específico de intervención"
        )
        
        # Additional details (optional)
        with st.expander("Detalles Adicionales (Opcional)"):
            additional_details = st.text_area(
                "Descripción adicional del proyecto",
                value=st.session_state.phase1_data.get('additional_details', ''),
                placeholder="Ej: Construcción de residencia unifamiliar de 2 niveles con piscina y gazebo",
                height=100
            )
            
            if additional_details:
                st.session_state.phase1_data['additional_details'] = additional_details
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("← Volver a Ubicación", use_container_width=True):
                st.session_state.phase1_step = 0
                st.rerun()
        
        with col2:
            if project_type and project_description:
                if st.button("Ver Resultado →", type="primary", use_container_width=True):
                    # Save data
                    st.session_state.phase1_data['project_type'] = project_type
                    st.session_state.phase1_data['project_description'] = project_description
                    
                    # Analyze compatibility
                    result = self._analyze_preliminary_compatibility()
                    st.session_state.phase1_result = result
                    
                    # Add to history
                    SessionManager.add_validation_to_history({
                        'type': 'phase1_enhanced',
                        'address': st.session_state.phase1_data['formatted_address'],
                        'municipality': st.session_state.phase1_data['municipality'],
                        'project_type': project_type,
                        'result': result['status'],
                        'timestamp': None  # Will be added by SessionManager
                    })
                    
                    st.session_state.phase1_step = 2
                    st.rerun()
            else:
                st.button("Completa todos los campos requeridos", disabled=True, use_container_width=True)
    
    def _render_step3_results(self):
        """Step 3: Preliminary results"""
        
        result = st.session_state.phase1_result
        
        st.markdown("### Resultado Preliminar")
        
        # Show project summary
        with st.expander("Resumen del Proyecto", expanded=False):
            st.write(f"**Ubicación:** {st.session_state.phase1_data['formatted_address']}")
            st.write(f"**Municipio:** {st.session_state.phase1_data['municipality']}")
            st.write(f"**Régimen:** {st.session_state.phase1_data['regime']}")
            st.write(f"**Tipo:** {st.session_state.phase1_data['project_type']}")
            st.write(f"**Descripción:** {st.session_state.phase1_data['project_description']}")
        
        st.markdown("---")
        
        # Result display based on status
        status = result['status']
        
        if status == 'compatible':
            self._render_compatible_result(result)
        elif status == 'incomplete':
            self._render_incomplete_result(result)
        else:  # not_compatible
            self._render_not_compatible_result(result)
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("← Modificar Proyecto", use_container_width=True):
                st.session_state.phase1_step = 1
                st.rerun()
        
        with col2:
            if st.button("Continuar a Validación Completa →", type="primary", use_container_width=True):
                st.session_state.phase1_step = 3
                st.rerun()
    
    def _render_step4_upsell(self):
        """Step 4: Upsell to Phase 2"""
        
        st.markdown("### Validación Completa (Fase 2)")
        
        result = st.session_state.phase1_result
        
        # Show preliminary result summary
        status_emoji = {
            'compatible': '✅',
            'incomplete': '⚠️',
            'not_compatible': '❌'
        }
        
        status_text = {
            'compatible': 'Compatible (Preliminar)',
            'incomplete': 'Requiere Información Adicional',
            'not_compatible': 'No Compatible (Preliminar)'
        }
        
        st.info(f"""
        **Resultado Preliminar:** {status_emoji[result['status']]} {status_text[result['status']]}
        
        **Conclusión:** {result['conclusion']}
        """)
        
        st.markdown("---")
        
        # Upsell content
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 3rem; border-radius: 20px; text-align: center;
                    color: white; margin: 2rem 0;">
            <h2 style="color: white;">🎯 Continúa con la Validación Completa</h2>
            <p style="font-size: 1.2rem; margin: 1.5rem 0;">
                Confirma el cumplimiento total antes de someter tu solicitud oficial
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### ✨ La Validación Completa Incluye:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Confirmación oficial del distrito de calificación**
            - Verificación contra Mapa Interactivo de PR
            - Validación de número de catastro/finca
            - Identificación precisa de distrito actual
            
            **Verificación de zonas sobrepuestas y planes especiales**
            - Zona Costanera (DRNA/ARPE)
            - Zona Histórica
            - Zona Agrícola (Reserva Agrícola)
            - Zona de Inundación
            - Planes Especiales municipales
            """)
        
        with col2:
            st.markdown("""
            **Evaluación de parámetros aplicables**
            - Cabida mínima de lote
            - Densidad permitida
            - Altura máxima
            - Retiros (frontal, lateral, trasero)
            - Cubierta máxima
            - Estacionamientos requeridos
            
            **Identificación de requisitos ministeriales vs. discrecionales**
            - Proceso aplicable (PCOC, CUB, etc.)
            - Documentos requeridos
            - Agencias concernidas
            - Tiempo estimado de tramitación
            """)
        
        st.markdown("---")
        st.markdown("### Reporte Técnico Estructurado")
        st.info("""
        Recibirás un reporte técnico profesional listo para incluir en tu expediente, con:
        - Análisis detallado de cumplimiento normativo
        - Memorial explicativo con análisis de IA
        - Checklist de documentos requeridos
        - Pasos siguientes específicos para tu proyecto
        - Referencias a artículos aplicables del Reglamento
        """)
        
        # CTA
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button(
                "Comenzar Validación Completa (Fase 2)",
                type="primary",
                use_container_width=True,
                key="start_phase2_validation"
            ):
                # Check if user has access
                user_plan = st.session_state.get('user_plan', 'professional')
                
                if user_plan == 'free':
                    st.warning("""
                    ### Feature Premium
                    
                    La Validación Completa (Fase 2) requiere Plan Profesional o superior.
                    
                    **Beneficios del Plan Profesional:**
                    - ✅ Validaciones Fase 1 ilimitadas
                    - ✅ 10 validaciones completas/mes
                    - ✅ Análisis de documentos con IA
                    - ✅ Reportes técnicos profesionales
                    - ✅ Memorial explicativo generado
                    - ✅ Soporte prioritario
                    
                    **Solo $99/mes**
                    """)
                    
                    if st.button("Ver Planes y Actualizar", key="upgrade_from_phase1"):
                        st.session_state.current_page = 'pricing'
                        st.rerun()
                else:
                    # Has access, navigate to Phase 2
                    st.session_state.current_page = 'pcoc_validation'
                    
                    # Pre-populate Phase 2 with Phase 1 data
                    st.session_state.pcoc_project_data = {
                        'name': f"Proyecto {st.session_state.phase1_data['project_type']}",
                        'address': st.session_state.phase1_data['formatted_address'],
                        'municipality': st.session_state.phase1_data['municipality'],
                        'project_type': st.session_state.phase1_data['project_type'],
                        'latitude': st.session_state.phase1_data['latitude'],
                        'longitude': st.session_state.phase1_data['longitude'],
                        'catastro': st.session_state.phase1_data.get('catastro', ''),
                        'regime': st.session_state.phase1_data['regime']
                    }
                    
                    st.rerun()
        
        # Alternative actions
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("← Nueva Validación", use_container_width=True):
                # Reset wizard
                st.session_state.phase1_step = 0
                st.session_state.phase1_data = {}
                st.session_state.phase1_result = None
                st.rerun()
        
        with col2:
            if st.button("Ir al Dashboard", use_container_width=True):
                st.session_state.current_page = 'dashboard'
                st.rerun()
    
    def _detect_regime(self, municipality: str) -> str:
        """Detect applicable regime (POT or RC)"""
        return "POT" if municipality in MUNICIPIOS_POT else "Reglamento Conjunto"
    
    def _analyze_preliminary_compatibility(self) -> Dict:
        """
        Analyze preliminary compatibility based on project type and location
        
        Returns:
            Dict with status, conclusion, observations, and recommendations
        """
        
        data = st.session_state.phase1_data
        project_type = data['project_type']
        municipality = data['municipality']
        regime = data['regime']
        
        # Get compatible district categories for this project type
        compatible_categories = PROYECTO_DISTRITO_MAP.get(project_type, [])
        
        # Get all districts
        all_districts = self.rules_db.get_zoning_districts()
        
        # Find potentially compatible districts
        compatible_districts = [
            d for d in all_districts
            if d.get('category') in compatible_categories
        ]
        
        # Determine status
        if len(compatible_districts) > 0:
            # Potentially compatible, but incomplete without exact district
            status = 'incomplete'
            conclusion = f"El uso propuesto ({project_type}) es potencialmente compatible con la normativa aplicable en {municipality}, sujeto a confirmación del distrito específico y parámetros regulatorios."
            
            observations = [
                f"El proyecto de tipo '{project_type}' puede ser compatible con los siguientes distritos:",
                ", ".join([f"{d['code']} ({d['name_es']})" for d in compatible_districts[:5]]),
                "",
                "**Se requiere información adicional:**",
                "• Confirmación del distrito de calificación específico del predio",
                "• Verificación de zonas sobrepuestas (costanera, agrícola, histórica, etc.)",
                "• Validación de parámetros específicos (cabida, retiros, altura, densidad)"
            ]
            
            if regime == "POT":
                observations.append(f"• Verificación de normativa específica del POT de {municipality}")
            
            recommendations = [
                "**Siguiente paso recomendado:** Continuar con la Validación Completa (Fase 2)",
                "",
                "La Validación Completa verificará:",
                "• Distrito exacto mediante Mapa Interactivo de PR",
                "• Zonas sobrepuestas y restricciones adicionales",
                "• Parámetros aplicables específicos del distrito",
                "• Requisitos documentales y proceso aplicable"
            ]
        
        elif project_type == "Histórico/Especial":
            # Special case - needs detailed analysis
            status = 'incomplete'
            conclusion = f"El proyecto de tipo '{project_type}' requiere evaluación especializada debido a su naturaleza especial."
            
            observations = [
                "**Proyectos históricos o especiales requieren análisis detallado:**",
                "• Verificación si el predio está en Zona Histórica",
                "• Confirmación de planes especiales aplicables",
                "• Evaluación de restricciones de conservación",
                "• Identificación de permisos especiales requeridos (SHPO, ICP, etc.)"
            ]
            
            recommendations = [
                "**Altamente recomendado:** Validación Completa (Fase 2) para proyectos históricos",
                "",
                "Estos proyectos típicamente requieren:",
                "• Consulta con Oficina Estatal de Conservación Histórica (SHPO)",
                "• Evaluación de impacto visual y arquitectónico",
                "• Cumplimiento con guías de diseño específicas",
                "• Proceso de revisión discrecional"
            ]
        
        else:
            # Likely not compatible
            status = 'not_compatible'
            conclusion = f"El uso propuesto ({project_type}) no parece ser compatible, de forma preliminar, con los distritos típicos en {municipality}."
            
            observations = [
                f"**El proyecto de tipo '{project_type}' presenta limitaciones preliminares:**",
                "• No se identificaron distritos claramente compatibles con este uso",
                "• Puede requerir cambio de zonificación (rezoning)",
                "• Puede requerir Consulta de Ubicación (CUB) ante Junta de Planificación",
                "",
                "**Posibles alternativas:**",
                "• Modificar el tipo de uso propuesto",
                "• Buscar predio en distrito compatible",
                "• Solicitar rezoning del predio actual",
                "• Evaluar si califica como uso accesorio o condicional"
            ]
            
            recommendations = [
                "**Recomendación:** Antes de proceder, considera:",
                "",
                "1. **Validación Completa (Fase 2):** Confirmar definitivamente la incompatibilidad y explorar excepciones",
                "2. **Consulta profesional:** Arquitecto o planificador puede identificar alternativas",
                "3. **Consulta de Ubicación (CUB):** Solicitar determinación oficial a Junta de Planificación",
                "",
                "En algunos casos, usos aparentemente incompatibles pueden ser permitidos como:",
                "• Usos accesorios",
                "• Usos condicionales (con permisos especiales)",
                "• Usos grandfathered (preexistentes)"
            ]
        
        return {
            'status': status,
            'conclusion': conclusion,
            'observations': observations,
            'recommendations': recommendations,
            'compatible_districts': [d['code'] for d in compatible_districts],
            'analysis_date': None  # Will be set by timestamp
        }
    
    def _render_compatible_result(self, result: Dict):
        """Render compatible result"""
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                    border: 3px solid #10b981; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">✅</div>
            <div style="font-size: 2rem; font-weight: 800; color: #065f46;">
                Compatible (Preliminar)
            </div>
            <div style="font-size: 1.1rem; color: #047857; margin-top: 1rem;">
                El uso propuesto es potencialmente compatible con la normativa aplicable
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Conclusión:")
        st.success(result['conclusion'])
        
        st.markdown("### Observaciones:")
        for obs in result['observations']:
            if obs:  # Skip empty lines
                st.markdown(obs)
        
        st.markdown("### 💡 Nota Importante:")
        st.warning("""
        **Este resultado es preliminar y está sujeto a validación de parámetros específicos:**
        - Confirmación del distrito exacto del predio
        - Cabida mínima de lote
        - Retiros, altura y cubierta
        - Estacionamientos requeridos
        - Zonas sobrepuestas (costanera, agrícola, etc.)
        - Planes especiales o normativa municipal específica
        
        **Recomendamos continuar con la Validación Completa (Fase 2) para confirmar cumplimiento total.**
        """)
    
    def _render_incomplete_result(self, result: Dict):
        """Render incomplete result"""
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                    border: 3px solid #f59e0b; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-size: 2rem; font-weight: 800; color: #92400e;">
                Incompleto – Requiere Información Adicional
            </div>
            <div style="font-size: 1.1rem; color: #b45309; margin-top: 1rem;">
                El uso propuesto podría ser compatible, pero se requiere validación específica
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Conclusión:")
        st.info(result['conclusion'])
        
        st.markdown("### Observaciones:")
        for obs in result['observations']:
            if obs:
                st.markdown(obs)
        
        st.markdown("### Nota Importante:")
        st.warning("""
        **Este análisis preliminar identifica compatibilidad potencial, pero requiere confirmación:**
        
        La Validación Completa (Fase 2) verificará:
        - Distrito exacto mediante Mapa Interactivo de PR
        - Zonas sobrepuestas y planes especiales
        - Parámetros específicos aplicables
        - Requisitos documentales y proceso aplicable
        
        **Continuar con validación completa te ayudará a:**
        - Evitar rechazos por información incompleta
        - Identificar requisitos antes de diseñar
        - Acelerar el proceso de permisos
        - Reducir riesgos y costos
        """)
        
        st.markdown("### Próximos Pasos Recomendados:")
        for rec in result['recommendations']:
            if rec:
                st.markdown(rec)
    
    def _render_not_compatible_result(self, result: Dict):
        """Render not compatible result"""
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                    border: 3px solid #ef4444; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">❌</div>
            <div style="font-size: 2rem; font-weight: 800; color: #991b1b;">
                No Compatible (Preliminar)
            </div>
            <div style="font-size: 1.1rem; color: #b91c1c; margin-top: 1rem;">
                El uso propuesto no parece ser compatible con la normativa aplicable
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Conclusión:")
        st.error(result['conclusion'])
        
        st.markdown("### Observaciones:")
        for obs in result['observations']:
            if obs:
                st.markdown(obs)
        
        st.markdown("### Importante:")
        st.warning("""
        **Este resultado se basa en una evaluación preliminar.**
        
        En algunos casos, puede existir compatibilidad mediante:
        - Usos accesorios o condicionales
        - Excepciones o varianzas
        - Derechos adquiridos (grandfathering)
        - Interpretación específica de la normativa
        
        **La Validación Completa (Fase 2) puede:**
        - Confirmar definitivamente la incompatibilidad
        - Identificar excepciones o alternativas viables
        - Orientar sobre proceso de rezoning si necesario
        - Sugerir modificaciones al proyecto para lograr compatibilidad
        """)
        
        st.markdown("### Alternativas y Próximos Pasos:")
        for rec in result['recommendations']:
            if rec:
                st.markdown(rec)


def render_enhanced_phase1(rules_db: RulesDatabase):
    """Render the enhanced Phase 1 wizard"""
    
    SessionManager.initialize()
    
    wizard = EnhancedPhase1Wizard(rules_db)
    wizard.render()