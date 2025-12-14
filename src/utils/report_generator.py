#PDF report generation
from fpdf import FPDF
from datetime import datetime
from typing import Dict
import io

class PDF(FPDF):
    """Custom PDF class with UTF-8 support"""
    def header(self):
        pass
    
    def footer(self):
        pass

class ReportGenerator:
    """Generate PDF validation reports"""
    
    @staticmethod
    def generate_pdf(validation_result: Dict) -> bytes:
        """Generate PDF report from validation results"""
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "PYXTEN - Reporte de Validacion", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        
        # Project Info
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Informacion del Proyecto", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.ln(3)
        
        # Clean text function to remove accents
        def clean_text(text):
            replacements = {
                'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
                'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
                'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
        
        # Property info
        pdf.cell(60, 6, "Direccion:", border=1)
        pdf.cell(0, 6, clean_text(validation_result["property_address"]), border=1, ln=True)
        
        pdf.cell(60, 6, "Municipio:", border=1)
        pdf.cell(0, 6, clean_text(validation_result["municipality"]), border=1, ln=True)
        
        pdf.cell(60, 6, "Zonificacion:", border=1)
        zone_text = f"{validation_result['zoning_district']['code']} - {clean_text(validation_result['zoning_district']['name'])}"
        pdf.cell(0, 6, zone_text, border=1, ln=True)
        
        pdf.cell(60, 6, "Uso Propuesto:", border=1)
        use_text = f"{validation_result['proposed_use']['code']} - {clean_text(validation_result['proposed_use']['name'])}"
        pdf.cell(0, 6, use_text, border=1, ln=True)
        
        pdf.ln(10)
        
        # Viability Status
        pdf.set_font("Arial", "B", 14)
        if validation_result["viable"]:
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 8, "PROYECTO VIABLE", ln=True)
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.cell(0, 8, "PROYECTO NO VIABLE", ln=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # Summary
        pdf.set_font("Arial", "", 11)
        summary = clean_text(validation_result["summary"])
        pdf.multi_cell(0, 6, summary)
        pdf.ln(5)
        
        # Validation Results
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Resultados de Validacion", ln=True)
        pdf.ln(3)
        
        for result in validation_result["validation_results"]:
            pdf.set_font("Arial", "B", 11)
            status = "[OK]" if result["passed"] else "[X]"
            pdf.cell(0, 6, f"{status} {clean_text(result['rule_name'])}", ln=True)
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(10)
            message = clean_text(result["message"])
            pdf.multi_cell(0, 5, message)
            
            pdf.set_font("Arial", "I", 9)
            pdf.cell(10)
            article = clean_text(result["article"])
            pdf.cell(0, 5, f"Referencia: {article}", ln=True)
            pdf.ln(3)
        
        # Next Steps
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Proximos Pasos Recomendados", ln=True)
        pdf.ln(3)
        
        pdf.set_font("Arial", "", 11)
        for step in validation_result["next_steps"]:
            step_clean = clean_text(step)
            pdf.multi_cell(0, 6, step_clean)
        
        # Footer
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(
            0, 5,
            "NOTA LEGAL: Este reporte es una pre-validacion automatizada basada en "
            "Tomo 6 del Reglamento Conjunto. No constituye una determinacion oficial "
            "de OGPe o la Junta de Planificacion. Se recomienda verificar con un "
            "Profesional Autorizado antes de someter solicitud formal."
        )
        
        # Return PDF as bytes
        return pdf.output(dest='S').encode('latin-1')
        