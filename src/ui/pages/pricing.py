# Pricing Page - Página de precios y planes
import streamlit as st

def render_pricing_page():
    """Renderiza la página de precios"""
    
    st.markdown("""
    <style>
        .pricing-header {
            text-align: center;
            padding: 2rem 0;
        }
        
        .pricing-title {
            font-size: 2.5rem;
            font-weight: 800;
            color: #10b981;
            margin-bottom: 0.5rem;
        }
        
        .pricing-subtitle {
            font-size: 1.2rem;
            color: #6b7280;
        }
        
        .pricing-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            height: 100%;
            transition: all 0.3s;
        }
        
        .pricing-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        }
        
        .pricing-card.featured {
            border: 3px solid #10b981;
            position: relative;
        }
        
        .featured-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
            color: white;
            padding: 0.25rem 1rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.85rem;
        }
        
        .plan-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: #374151;
            margin-bottom: 0.5rem;
        }
        
        .plan-price {
            font-size: 2.5rem;
            font-weight: 800;
            color: #10b981;
            margin: 1rem 0;
        }
        
        .plan-period {
            font-size: 1rem;
            color: #6b7280;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="pricing-header">
        <div class="pricing-title">Planes y Precios</div>
        <div class="pricing-subtitle">
            Elige el plan perfecto para tus necesidades de validación
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3 Columnas de pricing
    col1, col2, col3 = st.columns(3)
    
    # Plan Gratis
    with col1:
        st.markdown('<div class="pricing-card">', unsafe_allow_html=True)
        
        st.markdown('<div class="plan-name">Gratis</div>', unsafe_allow_html=True)
        st.markdown('<div class="plan-price">$0<span class="plan-period">/mes</span></div>', unsafe_allow_html=True)
        
        st.markdown("**Perfecto para probar Pyxten**")
        st.divider()
        
        features = [
            ("✅", "5 validaciones Fase 1/mes"),
            ("✅", "Reportes básicos en PDF"),
            ("✅", "Verificación de zonificación"),
            ("❌", "Sin guardar proyectos"),
            ("❌", "Sin validación PCOC"),
            ("❌", "Sin soporte prioritario"),
        ]
        
        for icon, feature in features:
            st.markdown(f"{icon} {feature}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Plan Actual", key="btn_free", disabled=True, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Plan Profesional (Featured)
    with col2:
        st.markdown('<div class="pricing-card featured">', unsafe_allow_html=True)
        st.markdown('<div class="featured-badge">🔥 MÁS POPULAR</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="plan-name">Profesional</div>', unsafe_allow_html=True)
        st.markdown('<div class="plan-price">$99<span class="plan-period">/mes</span></div>', unsafe_allow_html=True)
        
        st.markdown("**Para desarrolladores activos**")
        st.divider()
        
        features = [
            ("✅", "Validaciones Fase 1 ilimitadas"),
            ("✅", "10 validaciones PCOC/mes"),
            ("✅", "Proyectos guardados (en sesión)"),
            ("✅", "Memorial Explicativo generado"),
            ("✅", "Reportes premium con AI"),
            ("✅", "Soporte por email"),
            ("✅", "Validación de documentos con IA"),
        ]
        
        for icon, feature in features:
            st.markdown(f"{icon} {feature}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Comenzar Prueba", key="btn_pro", type="primary", use_container_width=True):
            st.info("""
            **¡Gracias por tu interés!**
            
            La funcionalidad de pagos estará disponible en Phase 3.
            
            Por ahora, contáctanos para acceso anticipado:
            - 📧 info@pyxten.com
            - 📞 (787) 506-0402
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Plan Empresarial
    with col3:
        st.markdown('<div class="pricing-card">', unsafe_allow_html=True)
        
        st.markdown('<div class="plan-name">Empresarial</div>', unsafe_allow_html=True)
        st.markdown('<div class="plan-price">$299<span class="plan-period">/mes</span></div>', unsafe_allow_html=True)
        
        st.markdown("**Para equipos y empresas**")
        st.divider()
        
        features = [
            ("✅", "Todo en Plan Profesional"),
            ("✅", "Validaciones PCOC ilimitadas"),
            ("✅", "API access para integración"),
            ("✅", "Soporte prioritario"),
            ("✅", "Onboarding personalizado"),
            ("✅", "Reportes customizados"),
            ("✅", "Acceso anticipado a features"),
        ]
        
        for icon, feature in features:
            st.markdown(f"{icon} {feature}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📞 Contactar Ventas", key="btn_enterprise", use_container_width=True):
            st.info("""
            **Hablemos de tus necesidades empresariales**
            
            Contáctanos para una demo personalizada:
            - 📧 info@pyxten.com
            - 📞 (787) 506-0402
            - 📅 [Agendar Demo](https://calendly.com/pyxten)
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Comparación detallada
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("## 📋 Comparación Detallada de Planes")
    
    comparison_data = {
        "Característica": [
            "Validaciones Fase 1 (Zonificación)",
            "Validaciones PCOC (Documentos)",
            "Proyectos Guardados",
            "Memorial Explicativo AI",
            "Reportes en PDF",
            "Validación con IA",
            "Soporte Email",
            "Soporte Prioritario",
            "API Access",
            "Onboarding Personalizado"
        ],
        "Gratis": [
            "5/mes",
            "❌",
            "❌",
            "❌",
            "Básico",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌"
        ],
        "Profesional": [
            "Ilimitadas",
            "10/mes",
            "✅ (Sesión)",
            "✅",
            "Premium",
            "✅",
            "✅",
            "❌",
            "❌",
            "❌"
        ],
        "Empresarial": [
            "Ilimitadas",
            "Ilimitadas",
            "✅ (DB)",
            "✅",
            "Custom",
            "✅",
            "✅",
            "✅",
            "✅",
            "✅"
        ]
    }
    
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # FAQ
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("## ❓ Preguntas Frecuentes")
    
    with st.expander("¿Qué incluye una validación Fase 1?"):
        st.markdown("""
        Una validación Fase 1 verifica:
        - ✅ Compatibilidad uso/zonificación
        - ✅ Cumplimiento Tomo 6
        - ✅ Determinación ministerial vs discrecional
        - ✅ Reporte en PDF
        """)
    
    with st.expander("¿Qué es la validación PCOC?"):
        st.markdown("""
        La validación PCOC analiza tus documentos de construcción:
        - 📄 Planos arquitectónicos
        - 📄 Certificación de cabida
        - 📄 Certificado de zonificación
        - 🤖 Usa IA para detectar errores y omisiones
        - 📋 Genera checklist de cumplimiento
        """)
    
    with st.expander("¿Puedo cambiar de plan?"):
        st.markdown("""
        Sí, puedes actualizar o bajar de plan en cualquier momento.
        Los cambios se reflejan en tu próximo ciclo de facturación.
        """)
    
    with st.expander("¿Ofrecen descuentos por anualidad?"):
        st.markdown("""
        Sí, al pagar anualmente obtienes:
        - 💰 2 meses gratis (ahorra 17%)
        - 🎁 Créditos extra de validaciones
        - 🔒 Precio garantizado por 12 meses
        """)
    
    # Call to Action Final
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-radius: 16px;">
        <h2 style="color: #10b981;">¿Listo para acelerar tus proyectos?</h2>
        <p style="font-size: 1.1rem; color: #374151;">
            Comienza con el plan Gratis y actualiza cuando lo necesites
        </p>
    </div>
    """, unsafe_allow_html=True)