"""
Mapa Interactivo PR Helper
Helper component for integrating with JP's Interactive Map
Since there's no API, this provides manual verification workflow
"""

import streamlit as st
from typing import Dict, List, Optional

class MapaInteractivoHelper:
    """Helper for Mapa Interactivo de la Junta de Planificación"""
    
    MAPA_BASE_URL = "https://gis.jp.pr.gov/mipr/"
    
    # Known overlay zones to detect
    ZONAS_SOBREPUESTAS = [
        "Zona Costanera",
        "Zona Histórica",
        "Reserva Agrícola",
        "Zona de Inundación (FEMA)",
        "Zona de Deslizamiento",
        "Humedal",
        "Área Natural Protegida",
        "Plan Especial Municipal",
        "Otra (especificar)"
    ]
    
    @staticmethod
    def render_verification_widget(latitude: float, longitude: float, municipality: str):
        """
        Renders interactive widget for manual verification with Mapa Interactivo
        
        Args:
            latitude: Property latitude
            longitude: Property longitude
            municipality: Municipality name
        """
        
        st.markdown("### 🗺️ Verificación con Mapa Interactivo de PR")
        
        st.info("""
        **Vamos a verificar tu propiedad en el Mapa Oficial de la Junta de Planificación**
        
        Este paso es crucial para confirmar:
        - ✅ Distrito exacto de calificación
        - ✅ Zonas sobrepuestas (costanera, histórica, etc.)
        - ✅ Planes especiales aplicables
        """)
        
        # Instructions
        with st.expander("📋 Instrucciones - ¿Cómo verificar?", expanded=True):
            st.markdown("""
            **Sigue estos pasos:**
            
            1. **Abre el Mapa Interactivo** usando el botón abajo
            2. **Busca tu propiedad** usando:
               - Las coordenadas pre-pobladas, o
               - La dirección en el buscador del mapa
            3. **Identifica la información** que aparece:
               - **Distrito de Calificación** (ej: R-I, C-L, etc.)
               - **Zonas sobrepuestas** (costanera, histórica, etc.)
               - **Planes especiales** (si aplican)
            4. **Ingresa la información** en los campos abajo
            
            💡 **Tip:** El distrito aparece cuando haces click sobre tu predio en el mapa.
            """)
            
            # Visual guide
            st.image("https://via.placeholder.com/600x200/10b981/FFFFFF?text=Aqui+ira+screenshot+del+Mapa+Interactivo", 
                    caption="Ejemplo: Distrito de calificación aparece al hacer click en el predio")
        
        # Open map button with coordinates
        map_url = MapaInteractivoHelper._build_map_url(latitude, longitude)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.link_button(
                "🗺️ Abrir Mapa Interactivo de PR",
                map_url,
                use_container_width=True
            )
        
        with col2:
            st.markdown(f"""
            <div style="padding: 0.5rem; background: #f3f4f6; border-radius: 8px; text-align: center;">
                <div style="font-size: 0.7rem; color: #6b7280;">Coordenadas</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #374151;">
                    {latitude:.6f}, {longitude:.6f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Manual input form
        st.markdown("### 📝 Ingresa la Información del Mapa")
        
        # District input
        distrito_input = st.text_input(
            "Distrito de Calificación *",
            placeholder="Ej: R-I, C-L, RT-A, etc.",
            help="Ingresa el código del distrito exactamente como aparece en el mapa",
            key="mapa_distrito"
        )
        
        # Catastro confirmation
        catastro_confirmado = st.text_input(
            "Número de Catastro (Confirmación)",
            placeholder="Si aparece en el mapa, confírmalo aquí",
            help="Verifica que el catastro coincida con lo que ingresaste",
            key="mapa_catastro"
        )
        
        # Overlay zones
        st.markdown("**Zonas Sobrepuestas Detectadas** (selecciona todas las que apliquen):")
        
        zonas_detectadas = []
        
        cols = st.columns(2)
        for i, zona in enumerate(MapaInteractivoHelper.ZONAS_SOBREPUESTAS):
            with cols[i % 2]:
                if st.checkbox(zona, key=f"zona_{i}"):
                    zonas_detectadas.append(zona)
        
        # Special plans
        plan_especial = st.text_input(
            "Plan Especial (si aplica)",
            placeholder="Ej: Plan Especial Santurce, Plan Culebra, etc.",
            help="Si el mapa muestra un plan especial, ingrésalo aquí",
            key="mapa_plan_especial"
        )
        
        # Additional observations
        observaciones = st.text_area(
            "Observaciones Adicionales",
            placeholder="Cualquier información adicional relevante del mapa...",
            height=100,
            key="mapa_observaciones"
        )
        
        # Validate and save
        st.markdown("---")
        
        if st.button("✅ Confirmar Información del Mapa", type="primary", use_container_width=True):
            if distrito_input:
                # Save to session state
                verification_data = {
                    'distrito_confirmado': distrito_input.strip().upper(),
                    'catastro_confirmado': catastro_confirmado,
                    'zonas_sobrepuestas': zonas_detectadas,
                    'plan_especial': plan_especial,
                    'observaciones': observaciones,
                    'verificado': True
                }
                
                st.session_state.mapa_verification = verification_data
                
                st.success("✅ Información del Mapa Interactivo confirmada")
                
                # Show summary
                with st.expander("📋 Ver Resumen de Verificación", expanded=True):
                    st.markdown(f"""
                    **Distrito Confirmado:** {distrito_input.strip().upper()}
                    
                    **Zonas Sobrepuestas:** {len(zonas_detectadas)}
                    """)
                    
                    if zonas_detectadas:
                        for zona in zonas_detectadas:
                            st.markdown(f"- ⚠️ {zona}")
                    
                    if plan_especial:
                        st.markdown(f"\n**Plan Especial:** {plan_especial}")
                    
                    if catastro_confirmado:
                        st.markdown(f"\n**Catastro Confirmado:** {catastro_confirmado}")
                
                return verification_data
            
            else:
                st.error("⚠️ Por favor ingresa el Distrito de Calificación")
                return None
        
        # Show previously verified data if exists
        if st.session_state.get('mapa_verification', {}).get('verificado'):
            st.success("✅ Ya verificaste esta información. Puedes modificarla arriba si es necesario.")
    
    @staticmethod
    def _build_map_url(latitude: float, longitude: float) -> str:
        """
        Build Mapa Interactivo URL with coordinates
        
        Note: Since we don't have API docs, this is a best-effort URL.
        May need adjustment based on actual map parameters.
        """
        
        # Try common GIS URL patterns
        # Option 1: Direct coordinate zoom
        url = f"{MapaInteractivoHelper.MAPA_BASE_URL}?center={latitude},{longitude}&zoom=17"
        
        # If the above doesn't work, fallback to base URL
        # Users can manually search using the search box
        return url
    
    @staticmethod
    def get_verification_data() -> Optional[Dict]:
        """Get verification data from session state"""
        return st.session_state.get('mapa_verification')
    
    @staticmethod
    def analyze_overlay_zones(zonas: List[str]) -> Dict:
        """
        Analyze detected overlay zones and provide recommendations
        
        Args:
            zonas: List of detected overlay zones
        
        Returns:
            Dict with analysis and recommendations
        """
        
        critical_zones = []
        warnings = []
        requirements = []
        
        for zona in zonas:
            if "Costanera" in zona:
                critical_zones.append(zona)
                warnings.append("Requiere permisos de DRNA y ARPE")
                requirements.append("Solicitar Determinación de No Afectación (DNA)")
                requirements.append("Puede requerir Estudio de Impacto Ambiental")
            
            elif "Histórica" in zona or "Histórico" in zona:
                critical_zones.append(zona)
                warnings.append("Requiere revisión de Oficina Estatal de Conservación Histórica (SHPO)")
                requirements.append("Evaluación de impacto visual")
                requirements.append("Cumplir con guías de diseño histórico")
            
            elif "Reserva Agrícola" in zona or "Agrícola" in zona:
                critical_zones.append(zona)
                warnings.append("Limitaciones en uso no agrícola")
                requirements.append("Verificar si uso es compatible con suelos agrícolas")
            
            elif "Inundación" in zona:
                critical_zones.append(zona)
                warnings.append("Zona de inundación FEMA - requiere elevación")
                requirements.append("Certificación de elevación (Elevation Certificate)")
                requirements.append("Seguro contra inundaciones obligatorio")
            
            elif "Deslizamiento" in zona:
                warnings.append("Requiere estudio geotécnico")
                requirements.append("Informe de ingeniero geotécnico")
                requirements.append("Medidas de mitigación de riesgo")
            
            elif "Humedal" in zona:
                critical_zones.append(zona)
                warnings.append("Humedal protegido - construcción muy restringida")
                requirements.append("Permiso de EPA y/o USACE")
                requirements.append("Delineación de humedal por especialista")
        
        return {
            'critical_zones': critical_zones,
            'warnings': warnings,
            'requirements': list(set(requirements)),  # Remove duplicates
            'has_critical': len(critical_zones) > 0,
            'total_zones': len(zonas)
        }
    
    @staticmethod
    def render_overlay_analysis(zonas: List[str]):
        """Render analysis of overlay zones"""
        
        if not zonas:
            st.success("✅ No se detectaron zonas sobrepuestas. Proyecto sin restricciones adicionales.")
            return
        
        analysis = MapaInteractivoHelper.analyze_overlay_zones(zonas)
        
        st.warning(f"""
        ### ⚠️ Zonas Sobrepuestas Detectadas: {analysis['total_zones']}
        
        Tu propiedad está ubicada en una o más zonas con regulaciones especiales.
        """)
        
        # Critical zones
        if analysis['has_critical']:
            st.error("### 🚨 Zonas Críticas:")
            for zona in analysis['critical_zones']:
                st.markdown(f"- **{zona}**")
        
        # Warnings
        if analysis['warnings']:
            st.markdown("### 📋 Advertencias Importantes:")
            for warning in analysis['warnings']:
                st.markdown(f"- ⚠️ {warning}")
        
        # Requirements
        if analysis['requirements']:
            st.markdown("### ✅ Requisitos Adicionales:")
            for req in analysis['requirements']:
                st.markdown(f"- {req}")
        
        st.info("""
        **💡 Recomendación:**
        
        Las zonas sobrepuestas requieren permisos y evaluaciones adicionales más allá del PCOC.
        
        Es altamente recomendable:
        - Consultar con un profesional autorizado (arquitecto/ingeniero)
        - Contactar las agencias concernidas temprano en el proceso
        - Considerar el tiempo y costo adicional de estos permisos
        """)


# Helper function for easy import
def render_mapa_verification(latitude: float, longitude: float, municipality: str):
    """Convenience function to render the verification widget"""
    helper = MapaInteractivoHelper()
    return helper.render_verification_widget(latitude, longitude, municipality)