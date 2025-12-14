# PDF report generation
from fpdf import FPDF
from datetime import datetime
from typing import Dict

class PDF(FPDF):
    """Custom PDF class"""
    def header(self):
        pass

    def footer(self):
        pass

class ReportGenerator:
    """Generate PDF validation reports"""

    @staticmethod
    def generate_pdf(validation_result: Dict) -> bytes:
        """Generate PDF report from validation results"""

        # Clean text function: keep latin-1 (Spanish accents), drop emojis/unicode
        def clean_text(text) -> str:
            if text is None:
                return ""
            text = str(text)
            return text.encode("latin-1", "ignore").decode("latin-1")

        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Header
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, clean_text("PYXTEN - Reporte de Validación"), ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, clean_text(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True, align="C")
        pdf.ln(10)

        # Project Info
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, clean_text("Información del Proyecto"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.ln(3)

        # Property info
        pdf.cell(60, 6, clean_text("Dirección:"), border=1)
        pdf.cell(0, 6, clean_text(validation_result.get("property_address", "")), border=1, ln=True)

        pdf.cell(60, 6, clean_text("Municipio:"), border=1)
        pdf.cell(0, 6, clean_text(validation_result.get("municipality", "")), border=1, ln=True)

        pdf.cell(60, 6, clean_text("Zonificación:"), border=1)
        zoning = validation_result.get("zoning_district", {}) or {}
        zone_text = f"{zoning.get('code','')} - {clean_text(zoning.get('name',''))}"
        pdf.cell(0, 6, clean_text(zone_text), border=1, ln=True)

        pdf.cell(60, 6, clean_text("Uso Propuesto:"), border=1)
        proposed = validation_result.get("proposed_use", {}) or {}
        use_text = f"{proposed.get('code','')} - {clean_text(proposed.get('name',''))}"
        pdf.cell(0, 6, clean_text(use_text), border=1, ln=True)

        pdf.ln(10)

        # Viability Status
        pdf.set_font("Arial", "B", 14)
        if validation_result.get("viable", False):
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 8, clean_text("PROYECTO VIABLE"), ln=True)
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.cell(0, 8, clean_text("PROYECTO NO VIABLE"), ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # Summary
        pdf.set_font("Arial", "", 11)
        summary = clean_text(validation_result.get("summary", ""))
        pdf.multi_cell(0, 6, summary)
        pdf.ln(5)

        # Validation Results
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, clean_text("Resultados de Validación"), ln=True)
        pdf.ln(3)

        for result in validation_result.get("validation_results", []):
            passed = bool(result.get("passed", False))
            status = "[OK]" if passed else "[X]"

            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, clean_text(f"{status} {result.get('rule_name','')}"), ln=True)

            pdf.set_font("Arial", "", 10)
            pdf.cell(10)
            message = clean_text(result.get("message", ""))
            pdf.multi_cell(0, 5, message)

            pdf.set_font("Arial", "I", 9)
            pdf.cell(10)
            article = clean_text(result.get("article", ""))
            pdf.cell(0, 5, clean_text(f"Referencia: {article}"), ln=True)
            pdf.ln(3)

        # Next Steps
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, clean_text("Próximos Pasos Recomendados"), ln=True)
        pdf.ln(3)

        pdf.set_font("Arial", "", 11)
        for step in validation_result.get("next_steps", []):
            pdf.multi_cell(0, 6, clean_text(step))

        # Footer
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(
            0, 5,
            clean_text(
                "NOTA LEGAL: Este reporte es una pre-validación automatizada basada en "
                "Tomo 6 del Reglamento Conjunto. No constituye una determinación oficial "
                "de OGPe o la Junta de Planificación. Se recomienda verificar con un "
                "Profesional Autorizado antes de someter solicitud formal."
            )
        )

        # Return PDF as bytes
        return pdf.output(dest="S").encode("latin-1")
        