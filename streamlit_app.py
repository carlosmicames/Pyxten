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
from src.ui.components.header import render_header
from src.ui.components.dashboard import render_dashboard
from src.ui.pages.pricing import render_pricing_page

# Page config
st.set_page_config(
    page_title="Pyxten - Validación Inteligente de Permisos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e5e7eb;
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

# Render Header (siempre visible)
render_header()

# Get current page from session
current_page = SessionManager.get_current_page()

# Route to appropriate page
if current_page == 'pricing':
    render_pricing_page()

elif current_page == 'dashboard':
    # Render Dashboard
    render_dashboard()
    
    st.markdown("---")
    st.markdown("## 🔍 Validación de Proyecto (Fase 1)")
    
    # Fase 1 Validation Form
    with st.container():
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        """, unsafe_allow_html=True)
        
        # Check if can validate
        if not SessionManager.can_validate():
            st.error("""
            ❌ **Has alcanzado el límite de validaciones gratuitas**
            
            Actualiza a Plan Profesional para validaciones ilimitadas.
            """)
            
            if st.button("💳 Ver Planes", key="upgrade_from_form"):
                SessionManager.navigate_to('pricing')
        else:
            # Show remaining validations
            remaining = SessionManager.get_remaining_validations()
            if remaining <= 2:
                st.warning(f"⚠️ Te quedan {remaining} validaciones gratuitas este mes")
            
            # Property Address
            property_address = st.text_input(
                "🏠 Dirección de la Propiedad",
                placeholder="Ej: Calle Luna 123, Urb. San Patricio, San Juan",
                help="Ingresa la dirección completa de la propiedad",
                key="prop_address"
            )
            
            # Two columns
            col1, col2 = st.columns(2)
            
            with col1:
                municipality = st.selectbox(
                    "🏛️ Municipio",
                    options=[""] + rules_db.get_municipalities(),
                    help="Selecciona el municipio",
                    index=0
                )
            
            with col2:
                zoning_options = [""] + [
                    f"{d['code']} - {d['name_es']}"
                    for d in rules_db.get_zoning_districts()
                ]
                
                zoning_selection = st.selectbox(
                    "📍 Distrito de Zonificación",
                    options=zoning_options,
                    help="Selecciona la zonificación",
                    index=0
                )
                
                zoning_code = zoning_selection.split(" - ")[0] if zoning_selection else ""
            
            # Proposed Use
            use_options = [""] + [
                f"{u['code']} - {u['name_es']}"
                for u in rules_db.get_use_types()
            ]
            
            use_selection = st.selectbox(
                "🏗️ Uso Propuesto",
                options=use_options,
                help="Selecciona el uso propuesto",
                index=0
            )
            
            use_code = use_selection.split(" - ")[0] if use_selection else ""
            
            # Additional info
            with st.expander("📝 Información Adicional (Opcional)"):
                project_description = st.text_area(
                    "Descripción del Proyecto",
                    placeholder="Ej: Construcción de residencia unifamiliar...",
                    help="Detalles adicionales"
                )
            
            # Validate button
            st.markdown("<br>", unsafe_allow_html=True)
            validate_button = st.button(
                "🔍 Validar Proyecto",
                use_container_width=True,
                type="primary"
            )
            
            # Validation logic
            if validate_button:
                if not all([property_address, municipality, zoning_code, use_code]):
                    st.error("⚠️ Por favor completa todos los campos requeridos")
                else:
                    with st.spinner("🔄 Validando proyecto contra Tomo 6..."):
                        validator = ZoningValidator(rules_db)
                        
                        result = validator.validate_project(
                            property_address=property_address,
                            municipality=municipality,
                            zoning_code=zoning_code,
                            proposed_use_code=use_code
                        )
                        
                        if "error" in result:
                            st.error(f"❌ Error: {result['error']}")
                        else:
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
                            
                            # Display results
                            st.markdown("---")
                            st.markdown("## 📊 Resultados de Validación")
                            
                            # Viability
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
                            st.markdown("### 📝 Resumen")
                            st.info(result["summary"])
                            
                            # Detailed results
                            st.markdown("### 📋 Validaciones Detalladas")
                            
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
                            st.markdown("### 📥 Descargar Reporte")
                            
                            pdf_bytes = ReportGenerator.generate_pdf(result)
                            st.download_button(
                                label="📄 Descargar Reporte PDF",
                                data=pdf_bytes,
                                file_name=f"pyxten_validacion_{municipality.replace(' ', '_').lower()}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            # Add to project if exists
                            if current_project:
                                SessionManager.add_report_to_project(
                                    current_project['id'],
                                    'fase1',
                                    pdf_bytes
                                )
                                st.success(f"✅ Reporte agregado al proyecto '{current_project['name']}'")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #6b7280;">
    <p style="font-weight: 600; margin-bottom: 0.5rem;">Pyxten LLC © 2025 | Desarrollado en Puerto Rico</p>
    <p style="font-size: 0.85rem; max-width: 900px; margin: 0 auto;">
        <em>Este informe es una pre-validación automatizada. No sustituye aprobaciones oficiales 
        de OGPe o la Junta de Planificación. Verifica con un Profesional Autorizado antes de someter solicitud formal.</em>
    </p>
    <div style="margin-top: 1rem; display: flex; justify-content: center; gap: 1.5rem;">
        <a href="#" style="color: #10b981; text-decoration: none;">Contacto</a>
        <a href="#" style="color: #10b981; text-decoration: none;">Términos</a>
        <a href="#" style="color: #10b981; text-decoration: none;">Privacidad</a>
    </div>
</div>
""", unsafe_allow_html=True)