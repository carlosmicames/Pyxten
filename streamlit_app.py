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
    initial_sidebar_state="collapsed"
)

# Custom CSS matching the image
st.markdown("""
<style>
    /* Main background gradient */
    .stApp {
        background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #14b8a6 100%);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Header styling */
    .pyxten-header {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    .pyxten-logo {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .pyxten-tagline {
        font-size: 1.1rem;
        color: #6b7280;
        font-weight: 500;
    }
    
    /* Content container */
    .content-wrapper {
        display: flex;
        gap: 2rem;
        margin-top: 2rem;
    }
    
    /* Sidebar card */
    .sidebar-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        flex: 0 0 300px;
    }
    
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #10b981;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .phase-item {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: #f0fdf4;
        border-left: 4px solid #10b981;
        border-radius: 8px;
        font-size: 0.9rem;
    }
    
    .phase-future {
        background: #f9fafb;
        border-left-color: #d1d5db;
        color: #6b7280;
    }
    
    /* Main form card */
    .form-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        flex: 1;
    }
    
    /* Input field styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #10b981;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.875rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
    }
    
    /* Results styling */
    .viable-box {
        padding: 2rem;
        border-radius: 16px;
        margin: 2rem 0;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        animation: slideIn 0.5s ease;
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
    
    .viable-yes {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border: 2px solid #10b981;
        color: #065f46;
    }
    
    .viable-no {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 2px solid #ef4444;
        color: #991b1b;
    }
    
    .rule-passed {
        background: #ecfdf5;
        padding: 1.25rem;
        border-left: 4px solid #10b981;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    .rule-failed {
        background: #fef2f2;
        padding: 1.25rem;
        border-left: 4px solid #ef4444;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f9fafb;
        border-radius: 12px;
        font-weight: 600;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        color: white;
        font-size: 0.9rem;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.875rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
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
        return None

# Load data
try:
    rules_db = load_database()
    claude_ai = load_ai()
except Exception as e:
    st.error(f"Error cargando datos: {str(e)}")
    st.stop()

# Header
st.markdown("""
<div class="pyxten-header">
    <div class="pyxten-logo">Py✗ten</div>
    <div class="pyxten-tagline">Accelerate Your Construction Permits with Intelligent Validation</div>
</div>
""", unsafe_allow_html=True)

# Main content layout
col_sidebar, col_main = st.columns([1, 2.5])

# Sidebar
with col_sidebar:
    st.markdown("""
    <div class="sidebar-card">
        <div class="sidebar-title">
            📋 Sobre Pyxten
        </div>
        <div class="phase-item">
            <strong>Fase 1</strong> valida la compatibilidad de uso y zonificación según Tomo 6 Reglamento Conjunto.
        </div>
        <div style="margin-top: 1.5rem; margin-bottom: 0.5rem; font-weight: 600; color: #6b7280;">
            Próximas fases:
        </div>
        <div class="phase-item phase-future">
            <strong>Fase 2:</strong> Validación completa de PCOC
        </div>
        <div class="phase-item phase-future">
            <strong>Fase 3:</strong> Integración con SBP
        </div>
        <div class="phase-item phase-future">
            <strong>Fase 4:</strong> Municipios
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main form
with col_main:
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    
    # Direccion de la propiedad
    property_address = st.text_input(
        "🏠 Dirección de la Propiedad",
        placeholder="Ej: Calle 123 #456, Urb. Las Flores, San Juan, PR 00926",
        help="Ingresa la dirección completa de la propiedad a validar",
        key="prop_address"
    )
    
    # Dos columnas para municipio y zonificación
    col1, col2 = st.columns(2)
    
    with col1:
        municipality = st.selectbox(
            "🏛️ Municipio",
            options=[""] + rules_db.get_municipalities(),
            help="Seleccione el municipio donde se ubica la propiedad",
            index=["", "Guaynabo"].index("Guaynabo") if "Guaynabo" in rules_db.get_municipalities() else 0
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
            help="Seleccione la zonificación de la propiedad",
            index=zoning_options.index("R-1 - Residencial Baja Densidad") if "R-1 - Residencial Baja Densidad" in zoning_options else 0
        )
        
        zoning_code = zoning_selection.split(" - ")[0] if zoning_selection else ""
    
    # Uso Propuesto
    use_options = [""] + [
        f"{u['code']} - {u['name_es']}"
        for u in rules_db.get_use_types()
    ]
    
    use_selection = st.selectbox(
        "🏗️ Uso Propuesto",
        options=use_options,
        help="Seleccione el uso que desea darle a la propiedad",
        index=use_options.index("COM-WAREHOUSE - Almacén") if "COM-WAREHOUSE - Almacén" in use_options else 0
    )
    
    use_code = use_selection.split(" - ")[0] if use_selection else ""
    
    # Informacion Adicional
    with st.expander("📝 Información Adicional (Opcional)"):
        project_description = st.text_area(
            "Descripción del Proyecto",
            placeholder="E.g., Construccion de residencia unifamiliar de dos pisos.",
            help="Proporcione detalles adicionales sobre su proyecto"
        )
    
    # Validate button
    st.markdown("<br>", unsafe_allow_html=True)
    validate_button = st.button(
        "🔍 Validate Project",
        use_container_width=True,
        type="primary"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Validation logic
if validate_button:
    # Input validation
    if not all([property_address, municipality, zoning_code, use_code]):
        st.error("Favor de completar todos los campos obligatorios antes de validar.")
    else:
        with st.spinner("Validando proyecto..."):
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
                st.error(f"Error: {result['error']}")
            else:
                # Store result in session state
                st.session_state['validation_result'] = result
                
                # Display results in main column
                with col_main:
                    st.markdown('<div class="form-card">', unsafe_allow_html=True)
                    
                    # Viability status
                    if result["viable"]:
                        st.markdown(
                            '<div class="viable-box viable-yes">✓ PROYECTO VIABLE</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div class="viable-box viable-no">✗ PROYECTO NO VIABLE</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Summary
                    st.markdown("### Resumen")
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
                    st.markdown("### Próximos Pasos Recomendados")
                    for i, step in enumerate(result["next_steps"], 1):
                        st.markdown(f"{i}. {step}")
                    
                    # Download report
                    st.markdown("---")
                    pdf_bytes = ReportGenerator.generate_pdf(result)
                    st.download_button(
                        label="Validar y Descargar Informe PDF",
                        data=pdf_bytes,
                        file_name=f"pyxten_validation_{municipality.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <p style="font-weight: 600; margin-bottom: 0.5rem;">Pyxten LLC © 2025 | Desarrollado en Puerto Rico</p>
    <p style="font-size: 0.85rem; opacity: 0.9; max-width: 900px; margin: 0 auto;">
        <em>Este informe ha sido generado por algoritmos basados en la interpretación legal del Reglamento Conjunto. Este documento constituye una pre-validación algorítmica y un 
        informe de debida diligencia legal. No es, ni sustituye, la aprobación o permiso oficial de la Junta de 
        Planificación de Puerto Rico, la Oficina de Gerencia de Permisos (OGPe) o cualquier municipio.</em>
    </p>
    <div style="margin-top: 1.5rem; display: flex; justify-content: center; gap: 1.5rem;">
        <a href="#" style="color: white; text-decoration: none;">Contact</a>
        <a href="#" style="color: white; text-decoration: none;">Terms</a>
        <a href="#" style="color: white; text-decoration: none;">Privacy</a>
    </div>
</div>
""", unsafe_allow_html=True)