"""
Simplified Phase 1 Wizard - 2 Steps
Step 1: Ubicación + Proyecto (combined)
Step 2: Resultado + Validación Completa (combined)
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


class SimplifiedPhase1Wizard:
    """Simplified Phase 1 wizard with 2 combined steps"""
    
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
        
        # Progress indicator (2 steps only)
        self._render_progress()
        
        # Render current step
        if st.session_state.phase1_step == 0:
            self._render_step1_combined()
        elif st.session_state.phase1_step == 1:
            self._render_step2_results_and_upsell()
    
    def _render_progress(self):
        """Progress indicator with 2 steps"""
        steps = ["Ubicación", "Proyecto", "Resultado", "Validación Completa"]
        current_main_step = st.session_state.phase1_step
        
        cols = st.columns(len(steps))
        for i, step in enumerate(steps):
            with cols[i]:
                # Steps 0-1 are in page 1, steps 2-3 are in page 2
                if current_main_step == 0:
                    # First page - show Ubicación and Proyecto as active
                    if i <= 1:
                        st.markdown(f"🔵 **{step}**")
                    else:
                        st.markdown(f"⚪ {step}")
                else:
                    # Second page - show all
                    if i <= 1:
                        st.markdown(f"✅ **{step}**")
                    else:
                        st.markdown(f"🔵 **{step}**")
        
        st.markdown("---")
    
    def _render_step1_combined(self):
        """Step 1: Combined Ubicación + Proyecto"""
        
        st.markdown("### 📍 Paso 1: Ubicación de la Propiedad")
        
        # Address input
        address = st.text_input(
            "Dirección de la Propiedad *",
            value=st.session_state.phase1_data.get('address', ''),
            placeholder="Ej: Calle Luna 123, San Juan",
            help="Dirección física completa de la propiedad"
        )
        
        # Validate address button
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🗺️ Validar Dirección con Google Maps", use_container_width=True):
                if not address:
                    st.error("Por favor ingresa una dirección")
                else:
                    with st.spinner("Validando dirección..."):
                        try:
                            validator = AddressValidator()
                            
                            # Try validation
                            result = validator.validate_address(
                                address=address,
                                municipality="",
                                country="Puerto Rico"
                            )
                            
                            if result['valid']:
                                st.success("✅ Dirección válida")
                                
                                # Extract municipality
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
                                
                                st.rerun()
                            
                            else:
                                st.error(f"❌ No se pudo validar la dirección")
                                st.warning("Verifica la dirección e intenta nuevamente")
                        
                        except ValueError as e:
                            st.error(f"Error: {str(e)}")
                            st.info("Asegúrate de tener GOOGLE_MAPS_API_KEY configurada en .env")
                        except Exception as e:
                            st.error(f"Error validando dirección: {str(e)}")
        
        # Show validated data if available
        if st.session_state.phase1_data.get('address_validated'):
            st.markdown("---")
            
            # Validated address display
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📍 Dirección Validada:**")
                st.write(st.session_state.phase1_data['formatted_address'])
            
            with col2:
                st.markdown("**🏛️ Municipio:**")
                st.write(st.session_state.phase1_data['municipality'])
            
            # Expandable map
            with st.expander("🗺️ Ver Ubicación en Mapa"):
                lat = st.session_state.phase1_data['latitude']
                lng = st.session_state.phase1_data['longitude']
                st.map(data=[[lat, lng]], zoom=15)
                st.caption(f"Coordenadas: {lat}, {lng}")
            
            # Catastro (optional)
            st.markdown("---")
            catastro = st.text_input(
                "Número de Catastro/Finca (Opcional)",
                value=st.session_state.phase1_data.get('catastro', ''),
                placeholder="Ej: 123-456-789",
                help="Será validado contra el Mapa Interactivo de PR en la validación completa"
            )
            
            if catastro:
                st.session_state.phase1_data['catastro'] = catastro
            
            # Detect regime
            municipality = st.session_state.phase1_data['municipality']
            regime = self._detect_regime(municipality)
            st.session_state.phase1_data['regime'] = regime
            
            # Regime display
            if regime == "POT":
                st.info(f"""
                📋 **Régimen Aplicable:** Plan de Ordenación Territorial (POT) Municipal
                
                El municipio de **{municipality}** cuenta con POT vigente.
                """)
            else:
                st.info(f"""
                📋 **Régimen Aplicable:** Reglamento Conjunto 2023
                
                El municipio de **{municipality}** aplica el Reglamento Conjunto.
                """)
            
            # --- PROJECT TYPE SECTION (SAME PAGE) ---
            st.markdown("---")
            st.markdown("### 🏗️ Tipo de Proyecto")
            
            col1, col2 = st.columns(2)
            
            with col1:
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
            
            with col2:
                project_description = st.selectbox(
                    "Descripción del Uso *",
                    options=[
                        "",
                        "Nueva Construcción",
                        "Remodelación",
                        "Cambio de Uso",
                        "Ampliación"
                    ],
                    help="Tipo específico de intervención"
                )
            
            # Additional details
            with st.expander("Detalles Adicionales (Opcional)"):
                additional_details = st.text_area(
                    "Descripción adicional",
                    value=st.session_state.phase1_data.get('additional_details', ''),
                    placeholder="Ej: Construcción de residencia unifamiliar de 2 niveles...",
                    height=100
                )
                
                if additional_details:
                    st.session_state.phase1_data['additional_details'] = additional_details
            
            # Submit button
            st.markdown("---")
            if project_type and project_description:
                if st.button("Ver Resultado de Compatibilidad →", type="primary", use_container_width=True):
                    # Save data
                    st.session_state.phase1_data['project_type'] = project_type
                    st.session_state.phase1_data['project_description'] = project_description
                    
                    # Analyze compatibility
                    result = self._analyze_preliminary_compatibility()
                    st.session_state.phase1_result = result
                    
                    # Add to history
                    SessionManager.add_validation_to_history({
                        'type': 'phase1_simplified',
                        'address': st.session_state.phase1_data['formatted_address'],
                        'municipality': municipality,
                        'project_type': project_type,
                        'result': result['status'],
                        'timestamp': None
                    })
                    
                    st.session_state.phase1_step = 1
                    st.rerun()
            else:
                st.button("Completa todos los campos requeridos", disabled=True, use_container_width=True)
        
        else:
            st.warning("⚠️ Valida tu dirección con Google Maps para continuar")
    
    def _render_step2_results_and_upsell(self):
        """Step 2: Combined Results + Upsell"""
        
        result = st.session_state.phase1_result
        
        # Show project summary in expandable
        with st.expander("📋 Resumen del Proyecto", expanded=False):
            st.write(f"**Ubicación:** {st.session_state.phase1_data['formatted_address']}")
            st.write(f"**Municipio:** {st.session_state.phase1_data['municipality']}")
            st.write(f"**Régimen:** {st.session_state.phase1_data['regime']}")
            st.write(f"**Tipo:** {st.session_state.phase1_data['project_type']}")
            st.write(f"**Descripción:** {st.session_state.phase1_data['project_description']}")
        
        st.markdown("---")
        
        # === RESULT SECTION ===
        st.markdown("## 📊 Resultado de Compatibilidad Preliminar")
        
        status = result['status']
        
        if status == 'compatible':
            self._render_compatible_result(result)
        elif status == 'incomplete':
            self._render_incomplete_result(result)
        else:
            self._render_not_compatible_result(result)
        
        # === COMBINED UPSELL SECTION (NO SEPARATE STEP) ===
        st.markdown("---")
        st.markdown("## 🚀 Confirma tu Proyecto con Validación Completa")
        
        st.info(f"""
        **Resultado Preliminar obtenido:** {self._get_status_text(status)}
        
        Para confirmar el cumplimiento total antes de someter tu solicitud oficial, continúa con la **Validación Completa (Fase 2)**.
        """)
        
        # Benefits in 2 columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### ✅ Verificaciones Incluidas:
            
            **📍 Confirmación Oficial:**
            - Distrito exacto de calificación
            - Validación con Mapa Interactivo PR
            - Número de catastro verificado
            
            **🗺️ Zonas Sobrepuestas:**
            - Zona Costanera (DRNA/ARPE)
            - Zona Histórica
            - Reserva Agrícola
            - Zonas de inundación
            - Planes especiales municipales
            """)
        
        with col2:
            st.markdown("""
            ### ✅ Análisis Detallado:
            
            **📐 Parámetros Aplicables:**
            - Cabida mínima de lote
            - Densidad permitida
            - Altura máxima
            - Retiros requeridos
            - Cubierta máxima
            - Estacionamientos
            
            **📄 Reporte Técnico:**
            - Memorial explicativo con IA
            - Checklist de documentos
            - Referencias normativas
            - Proceso aplicable (ministerial/discrecional)
            """)
        
        # CTA Button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button(
                "🚀 Continuar a Validación Completa (Fase 2)",
                type="primary",
                use_container_width=True,
                key="start_phase2_main"
            ):
                user_plan = st.session_state.get('user_plan', 'professional')
                
                if user_plan == 'free':
                    st.warning("""
                    ### ⚠️ Feature Premium
                    
                    La Validación Completa requiere Plan Profesional.
                    
                    **$99/mes incluye:**
                    - Validaciones Fase 1 ilimitadas
                    - 10 validaciones completas/mes
                    - Análisis de documentos con IA
                    - Reportes técnicos profesionales
                    """)
                    
                    if st.button("Ver Planes", key="upgrade_from_results"):
                        st.session_state.current_page = 'pricing'
                        st.rerun()
                else:
                    # Navigate to Phase 2 with pre-populated data
                    st.session_state.current_page = 'pcoc_validation'
                    
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
                st.session_state.phase1_step = 0
                st.session_state.phase1_data = {}
                st.session_state.phase1_result = None
                st.rerun()
        
        with col2:
            if st.button("📊 Ir al Dashboard", use_container_width=True):
                st.session_state.current_page = 'dashboard'
                st.rerun()
    
    def _detect_regime(self, municipality: str) -> str:
        """Detect applicable regime"""
        return "POT" if municipality in MUNICIPIOS_POT else "Reglamento Conjunto"
    
    def _get_status_text(self, status: str) -> str:
        """Get status display text"""
        status_map = {
            'compatible': '✅ Compatible (Preliminar)',
            'incomplete': '⚠️ Requiere Información Adicional',
            'not_compatible': '❌ No Compatible (Preliminar)'
        }
        return status_map.get(status, status)
    
    def _analyze_preliminary_compatibility(self) -> Dict:
        """Analyze preliminary compatibility"""
        
        data = st.session_state.phase1_data
        project_type = data['project_type']
        municipality = data['municipality']
        regime = data['regime']
        
        compatible_categories = PROYECTO_DISTRITO_MAP.get(project_type, [])
        all_districts = self.rules_db.get_zoning_districts()
        
        compatible_districts = [
            d for d in all_districts
            if d.get('category') in compatible_categories
        ]
        
        if len(compatible_districts) > 0:
            status = 'incomplete'
            conclusion = f"El uso propuesto ({project_type}) es potencialmente compatible con la normativa aplicable en {municipality}, sujeto a confirmación del distrito específico y parámetros regulatorios."
            
            observations = [
                f"El proyecto de tipo '{project_type}' puede ser compatible con los siguientes distritos:",
                ", ".join([f"{d['code']} ({d['name_es']})" for d in compatible_districts[:5]]),
                "",
                "**Se requiere información adicional:**",
                "• Confirmación del distrito de calificación específico",
                "• Verificación de zonas sobrepuestas",
                "• Validación de parámetros (cabida, retiros, altura)"
            ]
            
            if regime == "POT":
                observations.append(f"• Verificación de normativa del POT de {municipality}")
            
            recommendations = [
                "✅ **Recomendado:** Continuar con Validación Completa (Fase 2)",
                "",
                "Verificaremos:",
                "• Distrito exacto mediante Mapa Interactivo de PR",
                "• Zonas sobrepuestas y restricciones",
                "• Parámetros aplicables",
                "• Proceso de permisos requerido"
            ]
        
        elif project_type == "Histórico/Especial":
            status = 'incomplete'
            conclusion = "Proyectos históricos o especiales requieren evaluación especializada."
            
            observations = [
                "**Requiere análisis detallado:**",
                "• Verificar si está en Zona Histórica",
                "• Confirmar planes especiales",
                "• Evaluar restricciones de conservación"
            ]
            
            recommendations = [
                "⚠️ **Altamente recomendado:** Validación Completa para proyectos históricos",
                "",
                "Típicamente requieren:",
                "• Consulta con SHPO (Oficina Conservación Histórica)",
                "• Evaluación de impacto visual",
                "• Proceso discrecional"
            ]
        
        else:
            status = 'not_compatible'
            conclusion = f"El uso propuesto ({project_type}) no parece ser compatible preliminarmente con los distritos en {municipality}."
            
            observations = [
                f"**El proyecto '{project_type}' presenta limitaciones:**",
                "• No se identificaron distritos compatibles",
                "• Puede requerir rezoning",
                "• Puede requerir Consulta de Ubicación (CUB)",
                "",
                "**Alternativas posibles:**",
                "• Modificar el tipo de uso",
                "• Buscar predio en distrito compatible",
                "• Solicitar rezoning",
                "• Evaluar uso accesorio o condicional"
            ]
            
            recommendations = [
                "⚠️ **Antes de proceder:**",
                "",
                "1. Validación Completa puede identificar excepciones",
                "2. Consultar con arquitecto o planificador",
                "3. Considerar Consulta de Ubicación (CUB) oficial"
            ]
        
        return {
            'status': status,
            'conclusion': conclusion,
            'observations': observations,
            'recommendations': recommendations,
            'compatible_districts': [d['code'] for d in compatible_districts]
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
        </div>
        """, unsafe_allow_html=True)
        
        st.success(result['conclusion'])
        
        st.markdown("### 📝 Observaciones:")
        for obs in result['observations']:
            if obs:
                st.markdown(obs)
        
        st.warning("""
        **⚠️ Nota Importante:** Este resultado es preliminar.
        
        Se requiere validación de: distrito exacto, zonas sobrepuestas, cabida, retiros, altura, estacionamientos y otros parámetros.
        
        **Recomendamos continuar con Validación Completa para confirmar cumplimiento total.**
        """)
    
    def _render_incomplete_result(self, result: Dict):
        """Render incomplete result"""
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                    border: 3px solid #f59e0b; border-radius: 20px;
                    padding: 2.5rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-size: 2rem; font-weight: 800; color: #92400e;">
                Requiere Información Adicional
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(result['conclusion'])
        
        st.markdown("### 📝 Observaciones:")
        for obs in result['observations']:
            if obs:
                st.markdown(obs)
        
        st.warning("""
        **💡 Validación Completa verificará:**
        
        - ✅ Distrito exacto mediante Mapa Interactivo de PR
        - ✅ Zonas sobrepuestas y planes especiales
        - ✅ Parámetros específicos aplicables
        - ✅ Requisitos documentales
        
        **Esto te ayudará a evitar rechazos y acelerar tu proceso.**
        """)
    
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
        </div>
        """, unsafe_allow_html=True)
        
        st.error(result['conclusion'])
        
        st.markdown("### 📝 Observaciones:")
        for obs in result['observations']:
            if obs:
                st.markdown(obs)
        
        st.warning("""
        **⚠️ Importante:** Este resultado es preliminar.
        
        La Validación Completa puede:
        - Confirmar definitivamente la incompatibilidad
        - Identificar excepciones o alternativas viables
        - Orientar sobre proceso de rezoning
        - Sugerir modificaciones para lograr compatibilidad
        
        En algunos casos existen usos accesorios, condicionales o derechos adquiridos que pueden permitir el proyecto.
        """)


def render_simplified_phase1(rules_db: RulesDatabase):
    """Render the simplified Phase 1 wizard"""
    
    SessionManager.initialize()
    
    wizard = SimplifiedPhase1Wizard(rules_db)
    wizard.render()