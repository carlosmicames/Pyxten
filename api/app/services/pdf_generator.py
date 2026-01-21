"""
PDF Report Generator for Phase 1 Validations

CRITICAL WORDING REQUIREMENTS:
1) If viable: "El proyecto cumple con los requisitos de zonificacion en esa area."
2) If NOT viable: "El uso propuesto no es compatible con la zonificacion."
3) Remove "Proximos Pasos recomendados" section entirely
"""
from io import BytesIO
from datetime import datetime
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class PDFReportGenerator:
    """Generate PDF reports for Phase 1 validations"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(
            ParagraphStyle(
                "Title",
                parent=self.styles["Heading1"],
                fontSize=18,
                spaceAfter=12,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                "SubTitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=8,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ViableText",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.green,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "NotViableText",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.red,
                spaceAfter=6,
            )
        )

    def generate_report(
        self,
        validation_result: Dict,
        project_name: str,
        project_address: str,
        project_municipality: str,
    ) -> bytes:
        """
        Generate PDF report for a validation

        Args:
            validation_result: The validation result JSONB
            project_name: Name of the project
            project_address: Property address
            project_municipality: Municipality name

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []

        # Title
        story.append(
            Paragraph("Informe de Validacion Fase 1", self.styles["Title"])
        )
        story.append(Spacer(1, 12))

        # Report date
        story.append(
            Paragraph(
                f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        # Project info table
        project_data = [
            ["Proyecto:", project_name or "N/A"],
            ["Direccion:", project_address or "N/A"],
            ["Municipio:", project_municipality or "N/A"],
        ]

        final_result = validation_result.get("final_result", {})
        if final_result.get("zoning_code"):
            project_data.append(
                ["Zonificacion:", f"{final_result.get('zoning_code', 'N/A')} - {final_result.get('zoning_name', '')}"]
            )

        project_table = Table(project_data, colWidths=[1.5 * inch, 4.5 * inch])
        project_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(project_table)
        story.append(Spacer(1, 20))

        # Viability result - CRITICAL WORDING
        viable = final_result.get("viable", False)

        if viable:
            # Header for viable
            story.append(
                Paragraph("Proyecto Viable", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))
            # EXACT required text for viable
            story.append(
                Paragraph(
                    "El proyecto cumple con los requisitos de zonificacion en esa area.",
                    self.styles["ViableText"],
                )
            )
        else:
            # Header for not viable
            story.append(
                Paragraph("Resultado de Validacion", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))
            # EXACT required text for not viable
            story.append(
                Paragraph(
                    "El uso propuesto no es compatible con la zonificacion.",
                    self.styles["NotViableText"],
                )
            )

        story.append(Spacer(1, 20))

        # Uses validated section
        uses_validated = final_result.get("uses_validated", [])
        if uses_validated:
            story.append(
                Paragraph("Usos Evaluados", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))

            for use in uses_validated:
                use_text = f"- {use.get('name', use.get('code', 'N/A'))}"
                if use.get("interpretation"):
                    use_text += f": {use.get('interpretation')}"
                story.append(Paragraph(use_text, self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Compatibility details
        steps = validation_result.get("steps", {})
        compatibility = steps.get("5_compatibility_validation", {})
        individual_validations = compatibility.get("individual_validations", [])

        if individual_validations:
            story.append(
                Paragraph("Detalle de Compatibilidad", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))

            for val in individual_validations:
                status = "Compatible" if val.get("viable") else "No Compatible"
                val_text = f"- {val.get('use_name', val.get('use_code', 'N/A'))}: {status}"
                story.append(Paragraph(val_text, self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Overlay restrictions (if any)
        overlays = steps.get("6_overlay_restrictions", {})
        restrictions = overlays.get("restrictions", [])

        if restrictions:
            story.append(
                Paragraph("Restricciones Adicionales", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))

            for restriction in restrictions:
                story.append(
                    Paragraph(
                        f"- {restriction.get('restriction', 'N/A')}",
                        self.styles["Normal"],
                    )
                )

            story.append(Spacer(1, 12))

        # Warnings section
        warnings = validation_result.get("warnings", [])
        if warnings:
            story.append(
                Paragraph("Advertencias", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))

            for warning in warnings:
                story.append(Paragraph(f"- {warning}", self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Data sources
        data_sources = validation_result.get("data_sources", [])
        if data_sources:
            story.append(
                Paragraph("Fuentes de Datos", self.styles["SubTitle"])
            )
            story.append(Spacer(1, 6))

            for source in data_sources:
                story.append(
                    Paragraph(
                        f"- {source.get('source', 'N/A')}: {source.get('purpose', '')}",
                        self.styles["Normal"],
                    )
                )

            story.append(Spacer(1, 12))

        # Footer
        story.append(Spacer(1, 20))
        story.append(
            Paragraph(
                "Este informe es una evaluacion preliminar y no constituye un permiso oficial.",
                ParagraphStyle(
                    "Footer",
                    parent=self.styles["Normal"],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1,
                ),
            )
        )
        story.append(
            Paragraph(
                "Generado por Pyxten - Sistema de Validacion de Zonificacion",
                ParagraphStyle(
                    "Footer2",
                    parent=self.styles["Normal"],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1,
                ),
            )
        )

        # NOTE: "Proximos Pasos recomendados" section is intentionally NOT included
        # per the PDF text requirements

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes
