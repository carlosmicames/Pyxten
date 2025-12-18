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
from src.services.session_manager import SessionManager

# Import UI components
from src.ui.components.sidebar_nav import render_sidebar
from src.ui.components.homepage_validation import render_homepage
from src.ui.components.dashboard import render_dashboard
from src.ui.pages.pricing import render_pricing_page
from src.ui.pages.new_project import render_new_project_page
from src.ui.pages.active_projects import render_active_projects_page

# Page config
st.set_page_config(
    page_title="Pyxten - Validación Inteligente de Permisos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: #f9fafb;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
        border-right: 1px solid #e5e7eb;
    }
    
    [data-testid="stSidebar"] button {
        margin-bottom: 0.5rem;
        border-radius: 10px;
        border: 1px solid transparent;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] button:hover {
        border-color: #10b981;
        background: #ecfdf5;
    }
    
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Input field styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        transition: all 0.2s ease;
        background: white;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #10b981;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        outline: none;
    }
    
    /* Label styling */
    .stTextInput > label,
    .stSelectbox > label,
    .stTextArea > label {
        font-weight: 500;
        color: #374151;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #10b981 0%, #14b8a6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.875rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
        background: linear-gradient(90deg, #059669 0%, #0d9488 100%);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Secondary button */
    .stButton > button[kind="secondary"] {
        background: white;
        color: #374151;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: #f9fafb;
        border-color: #d1d5db;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.875rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
        width: 100%;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
    }
    
    /* Animations */
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
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    /* Form styling */
    .stForm {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        font-weight: 500;
        color: #374151;
        padding: 0.75rem 1rem;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #d1d5db;
        background: #f9fafb;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e5e7eb;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        background: white;
        border: 1px solid #e5e7eb;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #10b981 0%, #14b8a6 100%);
        color: white;
        border-color: #10b981;
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

# Initialize session
SessionManager.initialize()

# Render Sidebar Navigation
render_sidebar()

# Get current page from session
current_page = SessionManager.get_current_page()

# Default to homepage if not set
if not current_page or current_page == 'homepage':
    current_page = 'homepage'
    st.session_state.current_page = 'homepage'

# Route to appropriate page
try:
    if current_page == 'homepage':
        render_homepage(rules_db, claude_ai)
    
    elif current_page == 'dashboard':
        render_dashboard()
    
    elif current_page == 'new_project':
        render_new_project_page(rules_db)
    
    elif current_page == 'active_projects':
        render_active_projects_page()
    
    elif current_page == 'pricing':
        render_pricing_page()
    
    else:
        # Fallback to homepage
        st.warning(f"Página '{current_page}' no encontrada. Redirigiendo al inicio...")
        st.session_state.current_page = 'homepage'
        st.rerun()

except Exception as e:
    st.error(f"Error renderizando página: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #6b7280;">
    <p style="font-weight: 600; margin-bottom: 0.5rem;">Pyxten LLC © 2025 | Desarrollado en Puerto Rico 🇵🇷</p>
    <p style="font-size: 0.85rem; max-width: 900px; margin: 0 auto;">
        <em>Este informe es una pre-validación automatizada. No sustituye aprobaciones oficiales 
        de OGPe o la Junta de Planificación. Verifica con un Profesional Autorizado antes de someter solicitud formal.</em>
    </p>
    <div style="margin-top: 1rem; display: flex; justify-content: center; gap: 1.5rem;">
        <a href="mailto:info@pyxten.com" style="color: #10b981; text-decoration: none;">Contacto</a>
        <a href="#" style="color: #10b981; text-decoration: none;">Términos</a>
        <a href="#" style="color: #10b981; text-decoration: none;">Privacidad</a>
    </div>
</div>
""", unsafe_allow_html=True)
