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

        # Keep latin-1 (Spanish accents), drop emojis/unicode
        def clean_text(text) -> str:
            if text is None:
                return ""
            text = str(text)
            text = text.replace("\u00A0", " ")   # non-breaking space -> normal space
            text = text.replace("\u200B", "")    # zero-width space (if present)
            return text.encode("latin-1", "ignore").decode("latin-1")

        # Break long words so FPDF can wrap them (URLs, long codes, etc.)
        def wrap_long_words(text: str, max_chunk: int = 50) -> str:
            words = text.split(" ")
            out = []
            for w in words:
                if len(w) > max_chunk:
                    out.append("\n".join(w[i:i+max_chunk] for i in range(0, len(w), max_chunk)))
                else:
                    out.append(w)
            wrapped = " ".join(out)

            # Hard-wrap fallback in case something is still unbreakable
            lines = []
            for line in wrapped.split("\n"):
                if len(line) > 120:
                    lines.append("\n".join(line[i:i+120] for i in range(0, len(line), 120)))
                else:
                    lines.append(line)
            return "\n".join(lines)

        def safe_pdf_text(text) -> str:
            # Apply both protections consistently
            return wrap_long_words(clean_text(text))

        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.set_x(pdf.l_margin)

        # Header
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, safe_pdf_text("PYXTEN - Reporte de Validación"), ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, safe_pdf_text(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True, align="C")
        pdf.ln(10)

        # Project Info
        pdf.set_font("Arial", "B", 14)
        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(0, 8, safe_pdf_text("Información del Proyecto"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.ln(3)

        # Property info
        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(60, 6, safe_pdf_text("Dirección:"), border=1)
        pdf.cell(0, 6, safe_pdf_text(validation_result.get("property_address", "")), border=1, ln=True)

        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(60, 6, safe_pdf_text("Municipio:"), border=1)
        pdf.cell(0, 6, safe_pdf_text(validation_result.get("municipality", "")), border=1, ln=True)

        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(60, 6, safe_pdf_text("Zonificación:"), border=1)
        zoning = validation_result.get("zoning_district", {}) or {}
        zone_text = f"{zoning.get('code','')} - {zoning.get('name','')}"
        pdf.cell(0, 6, safe_pdf_text(zone_text), border=1, ln=True)

        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(60, 6, safe_pdf_text("Uso Propuesto:"), border=1)
        proposed = validation_result.get("proposed_use", {}) or {}
        use_text = f"{proposed.get('code','')} - {proposed.get('name','')}"
        pdf.cell(0, 6, safe_pdf_text(use_text), border=1, ln=True)

        pdf.ln(10)

        # Viability Status
        pdf.set_font("Arial", "B", 14)
        pdf.set_x(pdf.l_margin)  # Reset X position
        if validation_result.get("viable", False):
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 8, safe_pdf_text("PROYECTO VIABLE"), ln=True)
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.cell(0, 8, safe_pdf_text("PROYECTO NO VIABLE"), ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # Summary
        pdf.set_font("Arial", "", 11)
        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.multi_cell(0, 6, safe_pdf_text(validation_result.get("summary", "")))
        pdf.ln(5)

        # Validation Results
        pdf.set_font("Arial", "B", 14)
        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(0, 8, safe_pdf_text("Resultados de Validación"), ln=True)
        pdf.ln(3)

        for result in validation_result.get("validation_results", []):
            passed = bool(result.get("passed", False))
            status = "[OK]" if passed else "[X]"

            pdf.set_font("Arial", "B", 11)
            pdf.set_x(pdf.l_margin)  # Reset X position
            pdf.cell(0, 6, safe_pdf_text(f"{status} {result.get('rule_name','')}"), ln=True)

            pdf.set_font("Arial", "", 10)
            pdf.set_x(pdf.l_margin + 10)  # Indent
            pdf.multi_cell(0, 5, safe_pdf_text(result.get("message", "")))

            pdf.set_font("Arial", "I", 9)
            pdf.set_x(pdf.l_margin + 10)  # Indent
            pdf.cell(0, 5, safe_pdf_text(f"Referencia: {result.get('article','')}"), ln=True)
            pdf.ln(3)

        # Next Steps - FIX: Reset X position before multi_cell
        pdf.set_font("Arial", "B", 14)
        pdf.set_x(pdf.l_margin)  # Reset X position
        pdf.cell(0, 8, safe_pdf_text("Próximos Pasos Recomendados"), ln=True)
        pdf.ln(3)

        pdf.set_font("Arial", "", 11)
        for step in validation_result.get("next_steps", []):
            pdf.set_x(pdf.l_margin)  # FIX: Reset X position before each multi_cell
            pdf.multi_cell(0, 6, safe_pdf_text(step))

        # Footer
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.set_x(pdf.l_margin)  # Reset X position
        
        pdf.multi_cell(
            0, 5,
            safe_pdf_text(
                "NOTA LEGAL: Este reporte es una pre-validación automatizada basada en "
                "Tomo 6 del Reglamento Conjunto. No constituye una determinación oficial "
                "de OGPe o la Junta de Planificación. Se recomienda verificar con un "
                "Profesional Autorizado antes de someter solicitud formal."
            )
        )

        out = pdf.output(dest="S")
        return out if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")
