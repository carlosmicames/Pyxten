#PDF report generation
from fpdf import FPDF
from datetime import datetime
from typing import Dict

class ReportGenerator:
    """Generate PDF validation reports"""
    
    @staticmethod
    def generate_pdf(validation_result: Dict) -> bytes:
        """Generate PDF report from validation results"""
        
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "PYXTEN - Reporte de Validación", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        
        # Project Info
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Información del Proyecto", ln=True)
        pdf.set_font("Arial", "", 11)
        
        pdf.cell(60, 6, "Dirección:", border=1)
        pdf.cell(0, 6, validation_result["property_address"], border=1, ln=True)
        
        pdf.cell(60, 6, "Municipio:", border=1)
        pdf.cell(0, 6, validation_result["municipality"], border=1, ln=True)
        
        pdf.cell(60, 6, "Zonificación:", border=1)
        zone_text = f"{validation_result['zoning_district']['code']} - {validation_result['zoning_district']['name']}"
        pdf.cell(0, 6, zone_text, border=1, ln=True)
        
        pdf.cell(60, 6, "Uso Propuesto:", border=1)
        use_text = f"{validation_result['proposed_use']['code']} - {validation_result['proposed_use']['name']}"
        pdf.cell(0, 6, use_text, border=1, ln=True)
        
        pdf.ln(10)
        
        # Viability Status
        pdf.set_font("Arial", "B", 14)
        if validation_result["viable"]:
            pdf.set_text_color(0, 128, 0)  # Green
            pdf.cell(0, 8, "✓ PROYECTO VIABLE", ln=True)
        else:
            pdf.set_text_color(255, 0, 0)  # Red
            pdf.cell(0, 8, "✗ PROYECTO NO VIABLE", ln=True)
        
        pdf.set_text_color(0, 0, 0)  # Reset to black
        pdf.ln(5)
        
        # Summary
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, validation_result["summary"])
        pdf.ln(5)
        
        # Validation Results
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Resultados de Validación", ln=True)
        pdf.ln(3)
        
        for result in validation_result["validation_results"]:
            pdf.set_font("Arial", "B", 11)
            status = "✓" if result["passed"] else "✗"
            pdf.cell(0, 6, f"{status} {result['rule_name']}", ln=True)
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(10)  # Indent
            pdf.multi_cell(0, 5, result["message"])
            
            pdf.set_font("Arial", "I", 9)
            pdf.cell(10)  # Indent
            pdf.cell(0, 5, f"Referencia: {result['article']}", ln=True)
            pdf.ln(3)
        
        # Next Steps
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Próximos Pasos Recomendados", ln=True)
        pdf.ln(3)
        
        pdf.set_font("Arial", "", 11)
        for step in validation_result["next_steps"]:
            pdf.multi_cell(0, 6, step)
        
        # Footer
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(
            0, 5,
            "NOTA LEGAL: Este reporte es una pre-validación automatizada basada en "
            "Tomo 6 del Reglamento Conjunto. No constituye una determinación oficial "
            "de OGPe o la Junta de Planificación. Se recomienda verificar con un "
            "Profesional Autorizado antes de someter solicitud formal."
        )
        
        return pdf.output(dest='S').encode('latin-1')
