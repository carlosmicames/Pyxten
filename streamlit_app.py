import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import modules (Mocking these for the UI demo, ensure your files exist)
# from src.database.rules_loader import RulesDatabase
# from src.validators.zoning_validator import ZoningValidator
# from src.ai.claude_interpreter import ClaudeInterpreter
# from src.utils.report_generator import ReportGenerator

# --- MOCK CLASSES FOR UI TESTING (Remove when connecting to real backend) ---
class RulesDatabase:
    def get_municipalities(self): return ["Guaynabo", "San Juan", "Bayamón"]
    def get_zoning_districts(self): return [{"code": "R-1", "name_es": "Residencial Baja Densidad"}, {"code": "C-1", "name_es": "Comercial Liviano"}]
    def get_use_types(self): return [{"code": "COM-WAREHOUSE", "name_es": "Almacén"}, {"code": "RES-SINGLE", "name_es": "Residencia Unifamiliar"}]

# Page config
st.set_page_config(
    page_title="Pyxten - Validación de Permisos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Settings */
    .stApp {
        background-color: #F3F4F6; /* Light gray background */
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide standard Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Logo Area */
    .logo-container {
        padding: 1rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid #f3f4f6;
    }
    .logo-text {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -1px;
        color: #111827;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .logo-accent {
        color: #10B981; /* Emerald Green */
    }
    
    /* Sidebar Cards */
    .status-card {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .status-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6B7280;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    .status-item {
        font-size: 0.9rem;
        color: #374151;
        margin-bottom: 0.5rem;
        padding-left: 0.75rem;
        border-left: 3px solid #10B981;
    }
    .status-item-future {
        border-left: 3px solid #D1D5DB;
        color: #9CA3AF;
    }
    
    /* Main Content Styling */
    .main-header {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .form-container {
        background: white;
        padding: 2.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
    }
    
    /* Input Styling Override */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        color: #111827;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #10B981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }
    
    /* Button Styling */
    div.stButton > button {
        background: #10B981;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        border: none;
        width: 100%;
        transition: all 0.2s;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
    }
    div.stButton > button:hover {
        background: #059669;
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(16, 185, 129, 0.4);
    }

</style>
""", unsafe_allow_html=True)

# Initialize Logic
try:
    # Instantiate your actual classes here
    rules_db = RulesDatabase() 
    # claude_ai = ClaudeInterpreter() 
except Exception as e:
    st.error(f"System Error: {str(e)}")
    st.stop()

# --- SIDEBAR CONTENT ---
with st.sidebar:
    st.markdown("""
        <div class="logo-container">
            <div class="logo-text">
                Py<span class="logo-accent">><</span>ten
            </div>
            <div style="color: #6B7280; font-size: 0.9rem; margin-top: 0.5rem;">
                GovTech Intelligence
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="status-card">
            <div class="status-title">Estado del Sistema</div>
            <div class="status-item">
                <strong>Fase 1 (Activa)</strong><br>
                Validación de compatibilidad de uso y zonificación (Tomo 6).
            </div>
        </div>
        
        <div class="status-card">
            <div class="status-title">Roadmap</div>
            <div class="status-item status-item-future">
                <strong>Fase 2:</strong> Validación PCOC
            </div>
            <div class="status-item status-item-future">
                <strong>Fase 3:</strong> Integración SBP
            </div>
            <div class="status-item status-item-future">
                <strong>Fase 4:</strong> Municipios Autónomos
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 **Tip:** Tenga a la mano el número de catastro para futuras validaciones.")

# --- MAIN CONTENT ---

# 1. Main Header Area
st.markdown("""
    <div class="main-header">
        <div>
            <h1 style="margin:0; font-size: 1.8rem; color: #111827;">Validación de Proyectos</h1>
            <p style="margin:0; color: #6B7280; margin-top: 0.5rem;">Analiza la viabilidad legal de tu construcción en segundos.</p>
        </div>
        <div style="text-align: right;">
            <span style="background: #ECFDF5; color: #047857; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                🟢 Sistema Online
            </span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 2. Form Area (2 Column Grid)
with st.container():
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    st.subheader("📍 Detalles de la Propiedad")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 1: Address & Municipality
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        property_address = st.text_input(
            "Dirección Física",
            placeholder="Ej: Calle 123 #456, Urb. Las Flores",
            help="Dirección tal cual aparece en el documento legal."
        )
    
    with col2:
        municipality = st.selectbox(
            "Municipio",
            options=[""] + rules_db.get_municipalities(),
            index=0
        )

    # ROW 2: Zoning & Use
    col3, col4 = st.columns(2, gap="large")
    
    with col3:
        # Zoning Logic
        zoning_options = [""] + [f"{d['code']} - {d['name_es']}" for d in rules_db.get_zoning_districts()]
        zoning_selection = st.selectbox("Distrito de Zonificación", options=zoning_options)
        zoning_code = zoning_selection.split(" - ")[0] if zoning_selection else ""

    with col4:
        # Use Logic
        use_options = [""] + [f"{u['code']} - {u['name_es']}" for u in rules_db.get_use_types()]
        use_selection = st.selectbox("Uso Propuesto", options=use_options)
        use_code = use_selection.split(" - ")[0] if use_selection else ""

    # ROW 3: Description (Full Width)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📝 Información Adicional del Proyecto (Opcional)", expanded=False):
        project_description = st.text_area(
            "Descripción Técnica",
            placeholder="Describa altura, pies cuadrados aproximados, o detalles especiales...",
            height=100
        )

    # ACTION BUTTON
    st.markdown("<br>", unsafe_allow_html=True)
    validate_btn = st.button("🚀 Validar Viabilidad Legal")
    
    st.markdown('</div>', unsafe_allow_html=True)


# --- RESULTS SECTION (Conditional) ---
if validate_btn:
    if not all([property_address, municipality, zoning_code, use_code]):
        st.warning("⚠️ Por favor complete todos los campos requeridos para continuar.")
    else:
        # Placeholder for validation logic
        st.markdown("<br>", unsafe_allow_html=True)
        with st.spinner("Consultando Reglamento Conjunto 2020..."):
            import time
            time.sleep(1.5) # Fake loading for UX
            
            # --- MOCK RESULT ---
            st.success("Análisis completado")
            
            st.markdown("""
            <div style="background: white; padding: 2rem; border-radius: 16px; border-top: 5px solid #10B981; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                <h2 style="color: #065F46; margin-top:0;">✓ Proyecto Viable</h2>
                <p style="font-size: 1.1rem;">El uso propuesto es permitido en la zonificación seleccionada bajo clasificación <strong>Ministerial</strong>.</p>
                <hr style="border-top: 1px solid #eee; margin: 1.5rem 0;">
                <div style="display: flex; gap: 1rem;">
                    <button style="background: #EFF6FF; color: #1D4ED8; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer;">📄 Descargar Informe PDF</button>
                    <button style="background: white; color: #374151; border: 1px solid #D1D5DB; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer;">Enviar a Héctor</button>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #9CA3AF; font-size: 0.8rem;">
    Pyxten LLC © 2025. Uso exclusivo para validación preliminar.
</div>
""", unsafe_allow_html=True)