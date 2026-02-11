"""
PDF Report Generator for PCOC Validations
"""
from io import BytesIO
from datetime import datetime
from typing import Dict, Any

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


class PCOCPDFGenerator:
    """Generate PDF reports for PCOC validations"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(
            ParagraphStyle(
                "PCOCTitle",
                parent=self.styles["Heading1"],
                fontSize=18,
                spaceAfter=12,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                "PCOCSubTitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=8,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "PCOCSectionTitle",
                parent=self.styles["Heading3"],
                fontSize=12,
                spaceAfter=6,
                textColor=colors.HexColor("#1e40af"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ViableText",
                parent=self.styles["Normal"],
                fontSize=11,
                textColor=colors.green,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "WarningText",
                parent=self.styles["Normal"],
                fontSize=11,
                textColor=colors.HexColor("#d97706"),
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ActionItem",
                parent=self.styles["Normal"],
                fontSize=10,
                leftIndent=20,
                spaceAfter=4,
            )
        )

    def generate_report(self, validation) -> bytes:
        """
        Generate PDF report for a PCOC validation

        Args:
            validation: The PCOCValidation model instance

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
            Paragraph("Informe de Validacion PCOC", self.styles["PCOCTitle"])
        )
        story.append(
            Paragraph("Permiso de Construccion - Checklist de Pre-Validacion", self.styles["Normal"])
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
            ["Proyecto:", validation.project_name or "N/A"],
            ["Direccion:", validation.property_address or "N/A"],
            ["Municipio:", validation.municipality or "N/A"],
            ["Zonificacion:", validation.zoning_code or "N/A"],
        ]

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

        # Result summary
        result = validation.result or {}
        permit_type = result.get("permit_type", "")
        summary = result.get("summary", "")

        # Permit type header
        permit_type_display = {
            "obra_exenta": "OBRA EXENTA",
            "ministerial": "TRAMITE MINISTERIAL",
            "discrecional": "TRAMITE DISCRECIONAL",
        }.get(permit_type, permit_type.upper())

        story.append(
            Paragraph(f"Resultado: {permit_type_display}", self.styles["PCOCSubTitle"])
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph(summary, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        # Filter summaries
        filter_summary = result.get("filter_summary", {})

        story.append(
            Paragraph("Resumen de Filtros", self.styles["PCOCSectionTitle"])
        )
        story.append(Spacer(1, 6))

        filter_data = [
            ["Filtro", "Resultado"],
            ["Filtro 1: Obra Exenta", "Si" if filter_summary.get("filter1_exempt") else "No"],
            ["Filtro 2: Zonas Sobrepuestas", "Si" if filter_summary.get("filter2_has_overlays") else "No"],
            ["Filtro 3: Ministerial", "Si" if filter_summary.get("filter3_ministerial") else "No"],
            ["Filtro 4: Exclusion Categorica", "Si" if filter_summary.get("filter4_categorical_exclusion") else "No"],
        ]

        filter_table = Table(filter_data, colWidths=[3 * inch, 2 * inch])
        filter_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(filter_table)
        story.append(Spacer(1, 20))

        # Action items
        action_items = result.get("action_items", [])
        if action_items:
            story.append(
                Paragraph("Acciones Requeridas", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            for i, item in enumerate(action_items, 1):
                action_text = f"{i}. {item.get('action', 'N/A')}"
                story.append(Paragraph(action_text, self.styles["Normal"]))

                description = item.get("description", "")
                if description:
                    story.append(
                        Paragraph(f"   {description}", self.styles["ActionItem"])
                    )

                deadline = item.get("deadline", "")
                if deadline:
                    story.append(
                        Paragraph(f"   Plazo: {deadline}", self.styles["ActionItem"])
                    )

                story.append(Spacer(1, 4))

            story.append(Spacer(1, 12))

        # Recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            story.append(
                Paragraph("Recomendaciones", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Filter details
        self._add_filter_details(story, validation)

        # Footer
        story.append(Spacer(1, 30))
        story.append(
            Paragraph(
                "Este informe es una pre-validacion y no constituye un permiso oficial.",
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
                "Generado por Pyxten - Sistema de Validacion de Permisos de Construccion",
                ParagraphStyle(
                    "Footer2",
                    parent=self.styles["Normal"],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1,
                ),
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _add_filter_details(self, story, validation):
        """Add detailed filter information to the PDF"""

        # Filter 1 details
        filter1 = validation.filter1_data or {}
        if filter1:
            story.append(
                Paragraph("Detalle Filtro 1: Requiere Permiso?", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            proposed_use = filter1.get("proposed_use", "N/A")
            story.append(Paragraph(f"<b>Uso Propuesto:</b> {proposed_use}", self.styles["Normal"]))

            is_exempt = filter1.get("is_exempt", False)
            exempt_text = "Si, la obra es exenta" if is_exempt else "No, requiere permiso de construccion"
            story.append(Paragraph(f"<b>Obra Exenta:</b> {exempt_text}", self.styles["Normal"]))

            if filter1.get("exempt_reason"):
                story.append(Paragraph(f"<b>Razon:</b> {filter1.get('exempt_reason')}", self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Filter 2 details
        filter2 = validation.filter2_data or {}
        if filter2:
            story.append(
                Paragraph("Detalle Filtro 2: Zonas Sobrepuestas", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            zona_historica = "Si" if filter2.get("zona_historica") else "No"
            zona_turistica = "Si" if filter2.get("zona_turistica") else "No"
            zona_inundacion = "Si" if filter2.get("zona_inundacion") else "No"

            story.append(Paragraph(f"<b>Zona Historica (ZH/SH):</b> {zona_historica}", self.styles["Normal"]))
            story.append(Paragraph(f"<b>Zona de Interes Turistico (ZIT):</b> {zona_turistica}", self.styles["Normal"]))
            story.append(Paragraph(f"<b>Zona de Inundacion/Deslizamiento:</b> {zona_inundacion}", self.styles["Normal"]))

            required_recs = filter2.get("required_recommendations", [])
            if required_recs:
                story.append(Paragraph("<b>Recomendaciones Requeridas:</b>", self.styles["Normal"]))
                for rec in required_recs:
                    story.append(Paragraph(f"  • {rec.get('agency', 'N/A')}: {rec.get('requirement', 'N/A')}", self.styles["ActionItem"]))

            story.append(Spacer(1, 12))

        # Filter 3 details
        filter3 = validation.filter3_data or {}
        if filter3:
            story.append(
                Paragraph("Detalle Filtro 3: Clasificacion del Tramite", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            is_ministerial = filter3.get("is_ministerial")
            if is_ministerial is not None:
                ministerial_text = "Si - Tramite Ministerial" if is_ministerial else "No - Tramite Discrecional"
                story.append(Paragraph(f"<b>Ministerial:</b> {ministerial_text}", self.styles["Normal"]))

            non_compliant = filter3.get("non_compliant_params", [])
            if non_compliant:
                story.append(Paragraph(f"<b>Parametros No Conformes:</b> {', '.join(non_compliant)}", self.styles["Normal"]))

            story.append(Spacer(1, 12))

        # Filter 4 details
        filter4 = validation.filter4_data or {}
        if filter4:
            story.append(
                Paragraph("Detalle Filtro 4: Cumplimiento Ambiental", self.styles["PCOCSectionTitle"])
            )
            story.append(Spacer(1, 6))

            is_exc = filter4.get("is_categorical_exclusion", False)
            exc_text = "Si - Exclusion Categorica aplica" if is_exc else "No - Requiere EA o DIA"
            story.append(Paragraph(f"<b>Exclusion Categorica (OA 10-2025):</b> {exc_text}", self.styles["Normal"]))

            if filter4.get("exclusion_category"):
                story.append(Paragraph(f"<b>Categoria:</b> {filter4.get('exclusion_category')}", self.styles["Normal"]))

            if filter4.get("message"):
                story.append(Paragraph(f"<b>Nota:</b> {filter4.get('message')}", self.styles["Normal"]))

            story.append(Spacer(1, 12))
