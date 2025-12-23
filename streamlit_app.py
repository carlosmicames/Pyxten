import streamlit as st

# ⚠️ CRITICAL: set_page_config MUST be first
st.set_page_config(
    page_title="Pyxten - Validación Inteligente de Permisos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
from src.services.session_manager import SessionManager

# Import UI components
from src.ui.components.sidebar_nav import render_sidebar
from src.ui.components.homepage_validation import render_homepage
from src.ui.components.dashboard import render_dashboard
from src.ui.pages.pricing import render_pricing_page
from src.ui.pages.new_project import render_new_project_page
from src.ui.pages.active_projects import render_active_projects_page

# Phase 2 (PCOC) - Separate page
FASE2_AVAILABLE = False
model_router = None

try:
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if openai_key and anthropic_key:
        from src.ai.model_router import ModelRouter
        from src.validators.pcoc_validator import PCOCValidator
        from src.ui.pages.pcoc_validation import render_pcoc_validator
        FASE2_AVAILABLE = True
        st.sidebar.success("✅ Validación PCOC disponible")
    else:
        st.sidebar.warning("⚠️ APIs no configuradas - PCOC no disponible")
        
except Exception as e:
    st.sidebar.error(f"Error cargando Fase 2: {e}")

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: #f9fafb;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
        border-right: 1px solid #e5e7eb;
    }
    
    [data-testid="stSidebar"] button {
        margin-bottom: 0.5rem;
        border-radius: 10px;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] button:hover {
        border-color: #10b981;
        background: #ecfdf5;
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        padding: 0.75rem 1rem;
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
    
    .stButton > button {
        background: linear-gradient(90deg, #10b981 0%, #14b8a6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.875rem 2rem;
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
    
    .stDownloadButton > button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize
@st.cache_resource
def load_database():
    return RulesDatabase()

@st.cache_resource
def load_model_router():
    if not FASE2_AVAILABLE:
        return None
    try:
        from src.ai.model_router import ModelRouter
        return ModelRouter()
    except Exception as e:
        st.sidebar.error(f"Error ModelRouter: {e}")
        return None

# Load data
try:
    rules_db = load_database()
    model_router = load_model_router() if FASE2_AVAILABLE else None
except Exception as e:
    st.error(f"Error cargando datos: {str(e)}")
    st.stop()

# Initialize session
SessionManager.initialize()

# Render Sidebar
render_sidebar()

# Get current page
current_page = SessionManager.get_current_page()

if not current_page:
    current_page = 'homepage'
    st.session_state.current_page = 'homepage'

# Route to pages
try:
    if current_page == 'homepage':
        # PHASE 1 - Simplified single-page validation
        render_homepage(rules_db, None, model_router)
    
    elif current_page == 'dashboard':
        render_dashboard()
    
    elif current_page == 'new_project':
        render_new_project_page(rules_db)
    
    elif current_page == 'active_projects':
        render_active_projects_page()
    
    elif current_page == 'pricing':
        render_pricing_page()
    
    elif current_page == 'pcoc_validation':
        # PHASE 2 - Separate PCOC page
        if not FASE2_AVAILABLE:
            st.error("### Fase 2 (PCOC) No Disponible")
            st.warning("""
            Para habilitar la validación PCOC completa, necesitas:
            
            1. **OPENAI_API_KEY** - Para análisis de planos
            2. **ANTHROPIC_API_KEY** - Para análisis de documentos
            
            Verifica tu archivo `.env`
            """)
        elif not model_router:
            st.error("### Error Inicializando PCOC")
            st.info("Revisa el sidebar para más detalles")
        else:
            render_pcoc_validator(rules_db, model_router)
    
    else:
        st.warning(f"Página '{current_page}' no encontrada")
        st.session_state.current_page = 'homepage'
        st.rerun()

except Exception as e:
    st.error(f"Error: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #6b7280;">
    <p style="font-weight: 600; margin-bottom: 0.5rem;">
        Pyxten LLC © 2025 | Desarrollado en Puerto Rico 🇵🇷
    </p>
    <p style="font-size: 0.85rem;">
        <em>Este informe es una pre-validación automatizada. No sustituye aprobaciones 
        oficiales de OGPe o la Junta de Planificación.</em>
    </p>
</div>
""", unsafe_allow_html=True)