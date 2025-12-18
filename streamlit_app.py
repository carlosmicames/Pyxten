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

# Custom CSS Mejorado
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main background */
    .stApp {
        background: #fafafa;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* ===== FORMULARIO DE VALIDACIÓN ===== */
    .validation-form-container {
        background: white;
        padding: 2.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        margin-top: 2rem;
        border: 1px solid #e5e7eb;
    }
    
    .form-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .form-title {
        font-size: 2rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    
    .form-subtitle {
        font-size: 1rem;
        color: #6b7280;
    }
    
    /* Input Styling Mejorado */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        padding: 0.875rem 1rem;
        font-size: 0.95rem;
        transition: all 0.2s ease;
        background: #fafafa;
        font-weight: 500;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #10b981;
        box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1);
        outline: none;
        background: white;
    }
    
    /* Labels más prominentes */
    .stTextInput > label,
    .stSelectbox > label,
    .stTextArea > label {
        font-weight: 700;
        color: #111827;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
        display: block;
    }
    
    /* Help text */
    .stTextInput > div > div > div[data-testid="InputInstructions"],
    .stSelectbox > div > div > div[data-testid="InputInstructions"] {
        font-size: 0.85rem;
        color: #6b7280;
        margin-top: 0.35rem;
    }
    
    /* Button Styling Mejorado */
    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 1rem 2.5rem;
        font-size: 1rem;
        font-weight: 700;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Secondary buttons */
    div[data-testid="column"] .stButton > button {
        background: #f3f4f6;
        color: #374151;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    div[data-testid="column"] .stButton > button:hover {
        background: #e5e7eb;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }
    
    /* ===== RESULTADOS DE VALIDACIÓN ===== */
    .results-container {
        background: white;
        padding: 2.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        margin-top: 2rem;
        border: 1px solid #e5e7eb;
        animation: slideUp 0.5s ease;
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .viable-banner {
        padding: 2.5rem;
        border-radius: 16px;
        text-align: center;
        font-size: 1.75rem;
        font-weight: 900;
        margin: 2rem 0;
        animation: scaleIn 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }
    
    @keyframes scaleIn {
        from {
            transform: scale(0.9);
            opacity: 0;
        }
        to {
            transform: scale(1);
            opacity: 1;
        }
    }
    
    .viable-yes {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border: 3px solid #10b981;
        color: #065f46;
    }
    
    .viable-no {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 3px solid #ef4444;
        color: #991b1b;
    }
    
    /* Rule Cards */
    .rule-card {
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.25rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        transition: all 0.2s ease;
        border: 2px solid;
    }
    
    .rule-card:hover {
        transform: translateX(4px);
    }
    
    .rule-passed {
        background: #f0fdf4;
        border-color: #10b981;
    }
    
    .rule-failed {
        background: #fef2f2;
        border-color: #ef4444;
    }
    
    .rule-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .rule-message {
        font-size: 0.95rem;
        line-height: 1.6;
        margin: 0.75rem 0;
    }
    
    .rule-article {
        font-size: 0.85rem;
        font-style: italic;
        color: #6b7280;
        margin-top: 0.5rem;
    }
    
    /* Next Steps */
    .next-steps {
        background: #f9fafb;
        padding: 2rem;
        border-radius: 12px;
        margin-top: 2rem;
    }
    
    .next-steps ol {
        padding-left: 1.5rem;
    }
    
    .next-steps li {
        margin: 1rem 0;
        font-size: 1rem;
        line-height: 1.7;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 1rem 2.5rem;
        font-size: 1rem;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        width: 100%;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #10b981 !important;
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 10px;
        border: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    /* Divider */
    hr {
        margin: 3rem 0;
        border: none;
        border-top: 2px solid #e5e7eb;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 10px;
        font-weight: 600;
        color: #111827;
        padding: 1rem 1.25rem;
        transition: all 0.2s ease;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #10b981;
        background: #f9fafb;
    }
    
    /* Success/Error/Warning styling */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 10px;
        padding: 1rem 1.25rem;
        font-weight: 500;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 3rem 2rem;
        background: white;
        border-radius: 16px;
        margin-top: 3rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }
    
    .footer-title {
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
        font-size: 1rem;
    }
    
    .footer-disclaimer {
        font-size: 0.85rem;
        color: #6b7280;
        line-height: 1.6;
        max-width: 900px;
        margin: 1rem auto;
    }
    
    .footer-links {
        margin-top: 1.5rem;
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
    }
    
    .footer-link {
        color: #10b981;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .footer-link:hover {
        color: #059669;
        text-decoration: underline;
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
    st.error(f"❌ Error cargando datos: {str(e)}")
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
    
    # Validation Form Section
    st.markdown("---")
    
    st.markdown("""
    <div class="validation-form-container">
        <div class="form-header">
            <div class="form-title">🔍 Validación de Proyecto</div>
            <div class="form-subtitle">
                Valida tu proyecto contra el Reglamento Conjunto Tomo 6 en segundos
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Check if can validate
    if not SessionManager.can_validate():
        st.error("""
        ### ❌ Límite de Validaciones Alcanzado
        
        Has utilizado todas tus validaciones gratuitas este mes.
        
        **Actualiza a Plan Profesional para:**
        - ✅ Validaciones ilimitadas de Fase 1
        - ✅ 10 validaciones PCOC/mes con IA
        - ✅ Memorial Explicativo automático
        - ✅ Proyectos guardados
        - ✅ Reportes premium
        """)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("💳 Ver Planes y Precios", key="upgrade_from_form", type="primary", use_container_width=True):
                SessionManager.navigate_to('pricing')
    else:
        # Show remaining validations
        remaining = SessionManager.get_remaining_validations()
        if remaining <= 2:
            st.warning(f"⚠️ **Atención:** Te quedan solo {remaining} validaciones gratuitas este mes")
        else:
            st.info(f"ℹ️ Tienes {remaining} validaciones gratuitas restantes este mes")
        
        # Form Fields
        property_address = st.text_input(
            "🏠 Dirección de la Propiedad",
            placeholder="Ejemplo: Calle Luna 123, Urb. San Patricio, San Juan",
            help="Ingresa la dirección completa de la propiedad a validar",
            key="prop_address"
        )
        
        # Two columns for Municipality and Zoning
        col1, col2 = st.columns(2)
        
        with col1:
            municipality = st.selectbox(
                "🏛️ Municipio",
                options=["Selecciona un municipio..."] + rules_db.get_municipalities(),
                help="Municipio donde se ubica la propiedad",
                index=0
            )
        
        with col2:
            zoning_options = ["Selecciona una zonificación..."] + [
                f"{d['code']} - {d['name_es']}"
                for d in rules_db.get_zoning_districts()
            ]
            
            zoning_selection = st.selectbox(
                "📍 Distrito de Zonificación",
                options=zoning_options,
                help="Clasificación de zonificación de la propiedad según el Reglamento Conjunto",
                index=0
            )
            
            zoning_code = zoning_selection.split(" - ")[0] if zoning_selection and " - " in zoning_selection else ""
        
        # Proposed Use
        use_options = ["Selecciona un uso..."] + [
            f"{u['code']} - {u['name_es']}"
            for u in rules_db.get_use_types()
        ]
        
        use_selection = st.selectbox(
            "🏗️ Uso Propuesto",
            options=use_options,
            help="Tipo de uso o actividad que se desea realizar en la propiedad",
            index=0
        )
        
        use_code = use_selection.split(" - ")[0] if use_selection and " - " in use_selection else ""
        
        # Additional info (Optional)
        with st.expander("📝 Información Adicional (Opcional)", expanded=False):
            project_description = st.text_area(
                "Descripción del Proyecto",
                placeholder="Ejemplo: Construcción de residencia unifamiliar de 2 niveles con área de 2,500 pies cuadrados...",
                help="Proporciona detalles adicionales que puedan ayudar en la validación",
                height=120
            )
        
        # Validate button
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            validate_button = st.button(
                "🔍 Validar Proyecto Ahora",
                use_container_width=True,
                type="primary"
            )
        
        # Validation logic
        if validate_button:
            # Validation checks
            errors = []
            if not property_address:
                errors.append("• Dirección de la propiedad")
            if municipality == "Selecciona un municipio...":
                errors.append("• Municipio")
            if not zoning_code:
                errors.append("• Distrito de zonificación")
            if not use_code:
                errors.append("• Uso propuesto")
            
            if errors:
                st.error(f"⚠️ **Por favor completa los siguientes campos requeridos:**\n" + "\n".join(errors))
            else:
                with st.spinner("🔄 Validando proyecto contra Tomo 6 del Reglamento Conjunto..."):
                    validator = ZoningValidator(rules_db)
                    
                    result = validator.validate_project(
                        property_address=property_address,
                        municipality=municipality,
                        zoning_code=zoning_code,
                        proposed_use_code=use_code
                    )
                    
                    if "error" in result:
                        st.error(f"❌ **Error en la validación:** {result['error']}")
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
                        
                        # Success message
                        st.success("✅ **Validación completada exitosamente**")
                        
                        st.markdown('</div>', unsafe_allow_html=True)  # Close form container
                        
                        # Display Results
                        st.markdown('<div class="results-container">', unsafe_allow_html=True)
                        
                        st.markdown("## 📊 Resultados de Validación")
                        
                        # Viability Banner
                        if result["viable"]:
                            st.markdown(
                                '<div class="viable-banner viable-yes">✓ PROYECTO VIABLE</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                '<div class="viable-banner viable-no">✗ PROYECTO NO VIABLE</div>',
                                unsafe_allow_html=True
                            )
                        
                        # Summary
                        st.markdown("### 📝 Resumen Ejecutivo")
                        st.info(result["summary"])
                        
                        # Detailed Results
                        st.markdown("### 📋 Validaciones Detalladas")
                        
                        for val_result in result["validation_results"]:
                            status_class = "rule-passed" if val_result["passed"] else "rule-failed"
                            icon = "✓" if val_result["passed"] else "✗"
                            
                            st.markdown(
                                f"""
                                <div class="rule-card {status_class}">
                                    <div class="rule-title">{icon} {val_result['rule_name']}</div>
                                    <div class="rule-message">{val_result['message']}</div>
                                    <div class="rule-article">📖 {val_result['article']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        # Next Steps
                        st.markdown("""
                        <div class="next-steps">
                            <h3>📋 Próximos Pasos Recomendados</h3>
                        """, unsafe_allow_html=True)
                        
                        for i, step in enumerate(result["next_steps"], 1):
                            st.markdown(f"{i}. {step}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Download Section
                        st.markdown("---")
                        st.markdown("### 📥 Descargar Reporte")
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        
                        with col2:
                            pdf_bytes = ReportGenerator.generate_pdf(result)
                            st.download_button(
                                label="📄 Descargar Reporte Completo (PDF)",
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
                        
                        st.markdown('</div>', unsafe_allow_html=True)  # Close results container
                        
                        # End early to show results
                        st.stop()
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close form container

# Footer
st.markdown("""
<div class="footer">
    <div class="footer-title">Pyxten LLC © 2025 | Desarrollado en Puerto Rico</div>
    <div class="footer-disclaimer">
        <em>Este informe es una pre-validación automatizada basada en el Reglamento Conjunto Tomo 6. 
        No constituye una determinación oficial de OGPe o la Junta de Planificación. 
        Se recomienda verificar con un Profesional Autorizado (PA) antes de someter solicitud formal.</em>
    </div>
    <div class="footer-links">
        <a href="mailto:info@pyxten.com" class="footer-link">📧 Contacto</a>
        <a href="#" class="footer-link">📜 Términos</a>
        <a href="#" class="footer-link">🔒 Privacidad</a>
        <a href="#" class="footer-link">📚 Documentación</a>
    </div>
</div>
""", unsafe_allow_html=True)