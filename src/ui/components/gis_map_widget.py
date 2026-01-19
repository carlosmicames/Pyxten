import streamlit as st

def render_gis_map_link():
    """
    Renders prominent link/button to open MIPR GIS map in new tab

    This approach is better than iframe because:
    - Full-screen map experience
    - Access to all MIPR tools
    - No CORS restrictions
    - Better on mobile
    """

    st.markdown("""
    <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                border: 2px solid #10b981; border-radius: 16px; padding: 2rem;
                margin: 1.5rem 0; text-align: center;">
        <h3 style="color: #065f46; margin-bottom: 1rem;">
            Paso 1: Identifica tu Calificacion
        </h3>
        <p style="color: #047857; font-size: 1.05rem; margin-bottom: 1.5rem;">
            Usa el Mapa Oficial de la Junta de Planificacion para encontrar
            la calificacion de tu propiedad
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Prominent button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Use markdown link that opens in new tab
        st.markdown("""
        <a href="https://gis.jp.pr.gov/mipr/" target="_blank" style="text-decoration: none;">
            <button style="
                background: linear-gradient(90deg, #10b981 0%, #14b8a6 100%);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 1rem 2rem;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                width: 100%;
                transition: all 0.2s;
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(16, 185, 129, 0.4)';"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(16, 185, 129, 0.3)';">
                Abrir Mapa de Calificaciones MIPR
            </button>
        </a>
        """, unsafe_allow_html=True)

    # Instructions
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 12px;
                margin-top: 1.5rem; border-left: 4px solid #10b981;">
        <h4 style="color: #374151; margin-bottom: 1rem;">Como usar el mapa:</h4>
        <ol style="color: #6b7280; line-height: 1.8; margin: 0;">
            <li><strong>Busca tu direccion</strong> en el mapa (esquina superior derecha)</li>
            <li><strong>Haz zoom</strong> hasta ver tu propiedad claramente</li>
            <li><strong>Haz clic</strong> en tu propiedad (aparecera un popup)</li>
            <li><strong>Copia la "Calificacion"</strong> que aparece (ej: R-4, C-2, A-G)</li>
            <li><strong>Pegala</strong> en el formulario abajo</li>
        </ol>
        <p style="margin-top: 1rem; color: #9ca3af; font-size: 0.9rem;">
            <em>Consejo:</em> Puedes mantener el mapa abierto en otra pestana mientras llenas el formulario
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
