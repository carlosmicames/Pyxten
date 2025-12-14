import streamlit as st
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import modules
from src.database.rules_loader import RulesDatabase
from src.validators.zoning_validator import ZoningValidator
from src.ai.claude_interpreter import ClaudeInterpreter
from src.utils.report_generator import ReportGenerator

# Page config
st.set_page_config(
    page_title="Pyxten - Validación de Permisos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #0066CC;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .viable-box {
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .viable-yes {
        background-color: #d4edda;
        border: 2px solid #28a745;
        color: #155724;
    }
    .viable-no {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        color: #721c24;
    }
    .rule-passed {
        background-color: #d4edda;
        padding: 1rem;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .rule-failed {
        background-color: #f8d7da;
        padding: 1rem;
        border-left: 4px solid #dc3545;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize
@st.cache_resource
def load_database():
    return RulesDatabase()

@st.cache_resource
def load_ai():
    try:
        return ClaudeInterpreter()
    except ValueError:
        st.warning("⚠️ Claude AI no está configurado. Funcionalidad limitada.")
        return None

# Load data
try:
    rules_db = load_database()
    claude_ai = load_ai()
except Exception as e:
    st.error(f"Error cargando datos: {str(e)}")
    st.stop()

# Header
st.markdown('<div class="main-header">🏗️ PYXTEN</div>', unsafe_allow_html=rue)
st.markdown(
    '<div class="sub-header">Validación Inteligente de Permisos</div>',
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/0066CC/FFFFFF?text=PYXTEN", use_column_width=True)
    st.markdown("---")
    st.markdown("### 📋 Acerca de Pyxten")
    st.markdown("""
    **Fase 1** valida la compatibilidad de uso y zonificación según Tomo 6 del Reglamento Conjunto.
    
    **Próximas fases:**
    - Fase 2: Validación completa de PCOC
    - Fase 3: Integración con SBP
    - Fase 4: Municipios
    """)
    st.markdown("---")

# Main form
st.markdown("## Ingrese los datos del proyecto")

col1, col2 = st.columns(2)

with col1:
    property_address = st.text_input(
        "🏠 Dirección de la Propiedad",
        placeholder="Ej: Calle Luna 123, Urb. San Patricio",
        help="Ingrese la dirección completa de la propiedad"
    )
    
    municipality = st.selectbox(
        "🏛️ Municipio",
        options=[""] + rules_db.get_municipalities(),
        help="Seleccione el municipio donde se ubica la propiedad"
    )

with col2:
    # Get zoning districts for dropdown
    zoning_options = [""] + [
        f"{d['code']} - {d['name_es']}"
        for d in rules_db.get_zoning_districts()
    ]
    
    zoning_selection = st.selectbox(
        "📍 Distrito de Zonificación",
        options=zoning_options,
        help="Seleccione la zonificación de la propiedad"
    )
    
    # Extract zoning code
    zoning_code = zoning_selection.split(" - ")[0] if zoning_selection else ""
    
    # Get use types for dropdown
    use_options = [""] + [
        f"{u['code']} - {u['name_es']}"
        for u in rules_db.get_use_types()
    ]
    
    use_selection = st.selectbox(
        "🏗️ Uso Propuesto",
        options=use_options,
        help="Seleccione el uso que desea darle a la propiedad"
    )
    
    # Extract use code
    use_code = use_selection.split(" - ")[0] if use_selection else ""

# Additional info expander
with st.expander("Información Adicional (Opcional)"):
    project_description = st.text_area(
        "Descripción del Proyecto",
        placeholder="Ej: Construcción de residencia unifamiliar de 2 pisos...",
        help="Proporcione detalles adicionales sobre su proyecto"
    )

# Validate button
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    validate_button = st.button(
        "🔍 Validar Proyecto",
        type="primary",
        use_container_width=True
    )

# Validation logic
if validate_button:
    # Input validation
    if not all([property_address, municipality, zoning_code, use_code]):
        st.error("Por favor complete todos los campos requeridos")
    else:
        with st.spinner("🔄 Validando proyecto contra Tomo 6..."):
            # Create validator
            validator = ZoningValidator(rules_db)
            
            # Run validation
            result = validator.validate_project(
                property_address=property_address,
                municipality=municipality,
                zoning_code=zoning_code,
                proposed_use_code=use_code
            )
            
            # Check for errors
            if "error" in result:
                st.error(f" Error: {result['error']}")
            else:
                # Store result in session state
                st.session_state['validation_result'] = result
                
                # Display results
                st.markdown("---")
                st.markdown("## Resultados de Validación")
                
                # Viability status
                if result["viable"]:
                    st.markdown(
                        '<div class="viable-box viable-yes"> PROYECTO VIABLE</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div class="viable-box viable-no"> PROYECTO NO VIABLE</div>',
                        unsafe_allow_html=True
                    )
                
                # Summary
                st.markdown("### 📝 Resumen")
                st.info(result["summary"])
                
                # Detailed results
                st.markdown("### Validaciones Detalladas")
                
                for val_result in result["validation_results"]:
                    if val_result["passed"]:
                        st.markdown(
                            f"""
                            <div class="rule-passed">
                                <strong>✓ {val_result['rule_name']}</strong><br>
                                {val_result['message']}<br>
                                <small><em>{val_result['article']}</em></small>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="rule-failed">
                                <strong>✗ {val_result['rule_name']}</strong><br>
                                {val_result['message']}<br>
                                <small><em>{val_result['article']}</em></small>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                # Next steps
                st.markdown("### 📋 Próximos Pasos Recomendados")
                for i, step in enumerate(result["next_steps"], 1):
                    st.markdown(f"{i}. {step}")
                
                # Download report
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    pdf_bytes = ReportGenerator.generate_pdf(result)
                    st.download_button(
                        label="Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"pyxten_validacion_{municipality.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                # Contact info
                st.markdown("---")
                st.info("""
                ### 📞 ¿Necesita asistencia adicional?
                
                Para validaciones más complejas o consultas sobre permisos discrecionales, 
                contacte con nuestro equipo de expertos:
                
                Pyxten LLC | expertos@pyxten.com | (787) 506-0402
                """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>Pyxten LLC © 2025 | Desarrollado en Puerto Rico</p>
    <p><em>Este informe ha sido generado por algoritmos basados en la interpretación legal del [Insertar Nombre Oficial del Nuevo Reglamento Conjunto] y la Regla de Uso de Terrenos vigente. Este documento constituye una pre-validación algorítmica y un informe de debida diligencia legal. No es, ni sustituye, la aprobación o permiso oficial de la Junta de Planificación de Puerto Rico, la Oficina de Gerencia de Permisos (OGPe) o cualquier municipio. Pyxten no asume responsabilidad por cambios regulatorios, información de entrada incorrecta o errores en la discreción final de las agencias gubernamentales.</em></p>
</div>
""", unsafe_allow_html=True)
