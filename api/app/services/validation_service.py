"""
Phase 1 Validation Service
Ported from src/validators/integrated_validator.py
"""
from datetime import datetime
from typing import Dict, List, Optional

from app.services.arcgis_client import ArcGISPRClient
from app.services.address_validator import AddressValidator
from app.services.pot_equivalency import POTEquivalencyTable
from app.services.use_classifier import UseClassifier
from app.services.rules_data import get_rules_db


class Phase1ValidationService:
    """
    Phase 1 Validation Service

    Combines:
    1. Address geocoding with Google Maps
    2. ArcGIS lookup for zoning + overlays
    3. POT equivalencies
    4. Natural language use classification
    5. Zoning compatibility validation
    """

    def __init__(self):
        self.rules_db = get_rules_db()
        self.address_validator = AddressValidator()
        self.arcgis_client = ArcGISPRClient()
        self.pot_table = POTEquivalencyTable()
        self.use_classifier = UseClassifier(self.rules_db.get_use_types())

    def validate(
        self,
        address: str,
        municipality: str,
        project_description: str,
    ) -> Dict:
        """
        Main validation method

        Args:
            address: Property address
            municipality: Municipality name
            project_description: Natural language description of intended use

        Returns:
            Comprehensive validation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "input": {
                "address": address,
                "municipality": municipality,
                "project_description": project_description,
            },
            "steps": {},
            "final_result": {},
            "confidence": {"overall": 0.0, "factors": []},
            "warnings": [],
            "data_sources": [],
        }

        # STEP 1: Geocode address
        report["steps"]["1_geocoding"] = self._step_geocode(
            address, municipality, report
        )
        if not report["steps"]["1_geocoding"]["success"]:
            return self._early_exit(report, "geocoding_failed")

        coords = report["steps"]["1_geocoding"]["coordinates"]

        # STEP 2: Query ArcGIS for zoning
        report["steps"]["2_arcgis_lookup"] = self._step_arcgis_lookup(
            coords["latitude"], coords["longitude"], report
        )

        if not report["steps"]["2_arcgis_lookup"]["success"]:
            return self._early_exit(report, "arcgis_failed")

        # STEP 3: Handle POT equivalency if needed
        report["steps"]["3_pot_equivalency"] = self._step_pot_equivalency(
            report["steps"]["2_arcgis_lookup"], report
        )

        # STEP 4: Parse natural language use
        report["steps"]["4_use_classification"] = self._step_classify_use(
            project_description, report
        )

        if not report["steps"]["4_use_classification"]["uses"]:
            return self._early_exit(report, "use_classification_failed")

        # STEP 5: Validate each use against zoning
        report["steps"]["5_compatibility_validation"] = self._step_validate_compatibility(
            report["steps"]["3_pot_equivalency"]["final_zoning_code"],
            report["steps"]["4_use_classification"]["uses"],
            report,
        )

        # STEP 6: Check overlay restrictions
        report["steps"]["6_overlay_restrictions"] = self._step_check_overlays(
            report["steps"]["2_arcgis_lookup"].get("overlays", []),
            report["steps"]["4_use_classification"]["uses"],
            report,
        )

        # STEP 7: Generate final determination
        report["final_result"] = self._generate_final_result(report)

        # Calculate overall confidence
        report["confidence"] = self._calculate_confidence(report)

        return report

    def _step_geocode(self, address: str, municipality: str, report: Dict) -> Dict:
        """Step 1: Geocode address with Google Maps"""
        try:
            result = self.address_validator.validate_address(address, municipality)

            if result["valid"]:
                report["data_sources"].append(
                    {
                        "source": "Google Maps Geocoding API",
                        "purpose": "Address validation and coordinates",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                return {
                    "success": True,
                    "coordinates": {
                        "latitude": result["latitude"],
                        "longitude": result["longitude"],
                    },
                    "formatted_address": result["formatted_address"],
                    "confidence": result["confidence"],
                }
            else:
                report["warnings"].append(
                    f"Direccion no validada: {result.get('error')}"
                )
                return {
                    "success": False,
                    "error": result.get("error", "Address validation failed"),
                }

        except Exception as e:
            return {"success": False, "error": f"Error geocoding: {str(e)}"}

    def _step_arcgis_lookup(self, lat: float, lon: float, report: Dict) -> Dict:
        """Step 2: Query MIPR ArcGIS for zoning and overlays"""
        try:
            property_info = self.arcgis_client.get_complete_property_info(lat, lon)

            report["data_sources"].append(
                {
                    "source": "MIPR (Mapa Interactivo de Puerto Rico)",
                    "purpose": "Zoning district and overlay zones",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if property_info["zoning"]["error"]:
                return {
                    "success": False,
                    "error": property_info["zoning"]["error"],
                }

            return {
                "success": True,
                "zoning": property_info["zoning"],
                "overlays": property_info.get("overlays", []),
                "parcel": property_info.get("parcel"),
            }

        except Exception as e:
            return {"success": False, "error": f"Error querying ArcGIS: {str(e)}"}

    def _step_pot_equivalency(self, arcgis_result: Dict, report: Dict) -> Dict:
        """Step 3: Handle POT equivalency if municipal POT applies"""
        zoning = arcgis_result["zoning"]
        district_code = zoning["district_code"]

        if self.pot_table.is_municipal_specific(district_code):
            equivalent = self.pot_table.get_rc_equivalent(district_code, "2020")

            if equivalent:
                report["warnings"].append(
                    f"Distrito municipal '{district_code}' mapeado a RC 2020: '{equivalent['rc_code']}'"
                )

                report["data_sources"].append(
                    {
                        "source": "Tabla 6.1 - Reglamento Conjunto 2023",
                        "purpose": "POT district equivalency mapping",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                return {
                    "needs_equivalency": True,
                    "original_district": district_code,
                    "original_name": zoning["district_name"],
                    "equivalent": equivalent,
                    "final_zoning_code": equivalent["rc_code"],
                    "final_zoning_name": equivalent["rc_name"],
                }
            else:
                report["warnings"].append(
                    f"Distrito '{district_code}' no encontrado en tabla de equivalencias"
                )

                return {
                    "needs_equivalency": True,
                    "original_district": district_code,
                    "final_zoning_code": district_code,
                    "final_zoning_name": zoning["district_name"],
                    "warning": "Equivalencia no encontrada - usando codigo original",
                }
        else:
            return {
                "needs_equivalency": False,
                "final_zoning_code": district_code,
                "final_zoning_name": zoning["district_name"],
            }

    def _step_classify_use(self, project_description: str, report: Dict) -> Dict:
        """Step 4: Parse natural language use description"""
        try:
            result = self.use_classifier.parse_natural_language(project_description)

            report["data_sources"].append(
                {
                    "source": "OpenAI GPT-4o-mini",
                    "purpose": "Natural language use classification",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if result.get("clarifications_needed"):
                for clarif in result["clarifications_needed"]:
                    report["warnings"].append(f"Clarificacion: {clarif}")

            return result

        except Exception as e:
            return {
                "uses": [],
                "error": f"Error clasificando uso: {str(e)}",
            }

    def _step_validate_compatibility(
        self, zoning_code: str, classified_uses: List[Dict], report: Dict
    ) -> Dict:
        """Step 5: Validate each use against zoning"""
        validations = []

        for use in classified_uses:
            use_code = use["code"]
            use_type = self.rules_db.get_use_type(use_code)

            if not use_type:
                validations.append(
                    {
                        "use_code": use_code,
                        "viable": False,
                        "error": f"Tipo de uso '{use_code}' no encontrado",
                    }
                )
                continue

            compatible_zones = use_type.get("compatible_zones", [])
            is_compatible = zoning_code in compatible_zones
            is_ministerial = is_compatible and use_type.get("ministerial", False)

            validation_result = {
                "use_code": use_code,
                "use_name": use_type["name_es"],
                "viable": is_compatible,
                "is_ministerial": is_ministerial,
                "zoning_code": zoning_code,
                "compatible_zones": compatible_zones,
                "use_interpretation": use.get("interpretation", ""),
                "use_confidence": use.get("confidence", 0),
                "message": self._get_compatibility_message(
                    is_compatible, zoning_code, use_type
                ),
            }
            validations.append(validation_result)

        all_viable = all(v["viable"] for v in validations)
        any_ministerial = any(v.get("is_ministerial", False) for v in validations)

        return {
            "individual_validations": validations,
            "all_uses_compatible": all_viable,
            "has_ministerial_path": any_ministerial,
            "total_uses_validated": len(validations),
        }

    def _get_compatibility_message(
        self, is_compatible: bool, zoning_code: str, use_type: Dict
    ) -> str:
        """Generate compatibility validation message"""
        if is_compatible:
            return (
                f"El uso '{use_type['name_es']}' ES COMPATIBLE con la "
                f"zonificacion {zoning_code}"
            )
        else:
            compatible_list = ", ".join(use_type.get("compatible_zones", []))
            return (
                f"El uso '{use_type['name_es']}' NO ES COMPATIBLE con la "
                f"zonificacion {zoning_code}. Este uso solo se permite en: {compatible_list}"
            )

    def _step_check_overlays(
        self, overlays: List[Dict], classified_uses: List[Dict], report: Dict
    ) -> Dict:
        """Step 6: Check if overlay zones impose additional restrictions"""
        if not overlays:
            return {"has_overlays": False, "restrictions": []}

        restrictions = []

        for overlay in overlays:
            overlay_type = overlay.get("type", "") or overlay.get("overlay_type", "")

            if "Historica" in overlay_type or "historica" in overlay_type.lower():
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Requiere aprobacion del Instituto de Cultura Puertorriquena (ICP)",
                        "severity": "high",
                    }
                )
                report["warnings"].append(
                    "Propiedad en Zona Historica - Requiere aprobacion ICP"
                )

            if "Costanera" in overlay_type or "costanera" in overlay_type.lower():
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Regulado por Ley de Zona Costanera - Requiere permiso DRNA",
                        "severity": "high",
                    }
                )
                report["warnings"].append(
                    "Propiedad en Zona Costanera - Restricciones adicionales aplican"
                )

            if (
                "Inundacion" in overlay_type
                or "FEMA" in overlay_type
                or "inundacion" in overlay_type.lower()
            ):
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Area de riesgo a inundacion - Restricciones de construccion",
                        "severity": "high",
                    }
                )
                report["warnings"].append(
                    "Area de Riesgo a Inundacion - Restricciones especiales"
                )

        return {
            "has_overlays": len(overlays) > 0,
            "overlays_detected": overlays,
            "restrictions": restrictions,
            "requires_additional_permits": len(restrictions) > 0,
        }

    def _generate_final_result(self, report: Dict) -> Dict:
        """Step 7: Generate final determination"""
        compatibility = report["steps"]["5_compatibility_validation"]
        overlays = report["steps"]["6_overlay_restrictions"]
        uses = report["steps"]["4_use_classification"]["uses"]

        viable = compatibility["all_uses_compatible"]

        if viable:
            if overlays["requires_additional_permits"]:
                permit_type = "discrecional (overlays)"
            elif compatibility["has_ministerial_path"]:
                permit_type = "ministerial"
            else:
                permit_type = "discrecional"
        else:
            permit_type = "no_aplica"

        if viable:
            summary = f"COMPATIBLE - El uso propuesto es compatible con la zonificacion {report['steps']['3_pot_equivalency']['final_zoning_code']}"
        else:
            summary = f"NO COMPATIBLE - El uso propuesto no es permitido en zonificacion {report['steps']['3_pot_equivalency']['final_zoning_code']}"

        recommendations = []

        if viable:
            if permit_type == "ministerial":
                recommendations.append("1. Preparar documentos para Permiso Unico")
                recommendations.append("2. Contratar Profesional Autorizado (PA)")
                recommendations.append("3. Someter solicitud a OGPe o municipio")
            else:
                recommendations.append("1. Solicitar Consulta de Ubicacion (CUB)")
                recommendations.append("2. Preparar estudios tecnicos requeridos")
                recommendations.append("3. Coordinar con agencias concernidas")
        else:
            recommendations.append("1. Considerar cambio de zonificacion (rezoning)")
            recommendations.append("2. Modificar uso propuesto")
            recommendations.append("3. Buscar propiedad en zonificacion compatible")

        if overlays["requires_additional_permits"]:
            for restriction in overlays["restrictions"]:
                recommendations.append(f"- {restriction['restriction']}")

        return {
            "viable": viable,
            "permit_type": permit_type,
            "summary": summary,
            "uses_validated": uses,
            "total_uses": len(uses),
            "mixed_use": len(uses) > 1,
            "recommendations": recommendations,
            "zoning_code": report["steps"]["3_pot_equivalency"]["final_zoning_code"],
            "zoning_name": report["steps"]["3_pot_equivalency"]["final_zoning_name"],
        }

    def _calculate_confidence(self, report: Dict) -> Dict:
        """Calculate overall confidence score"""
        factors = []
        scores = []

        geocode = report["steps"]["1_geocoding"]
        if geocode.get("confidence") == "ROOFTOP":
            factors.append("address_exact")
            scores.append(1.0)
        elif geocode.get("success"):
            factors.append("address_approximate")
            scores.append(0.8)

        arcgis = report["steps"]["2_arcgis_lookup"]
        if arcgis["zoning"].get("confidence") == "high":
            factors.append("zoning_confirmed")
            scores.append(1.0)
        else:
            factors.append("zoning_uncertain")
            scores.append(0.6)

        use_class = report["steps"]["4_use_classification"]
        if use_class.get("uses"):
            avg_use_confidence = sum(u.get("confidence", 0.5) for u in use_class["uses"]) / len(
                use_class["uses"]
            )
            factors.append("use_classified")
            scores.append(avg_use_confidence)

        overlays = report["steps"]["6_overlay_restrictions"]
        if overlays["has_overlays"]:
            factors.append("overlays_detected")
            scores.append(0.9)
        else:
            factors.append("no_overlays")
            scores.append(1.0)

        overall = sum(scores) / len(scores) if scores else 0.0

        return {
            "overall": overall,
            "factors": factors,
            "meets_95_percent_target": overall >= 0.95,
        }

    def _early_exit(self, report: Dict, reason: str) -> Dict:
        """Handle early exit with error"""
        error_messages = {
            "geocoding_failed": "No se pudo validar la direccion",
            "arcgis_failed": "No se pudo obtener informacion de zonificacion",
            "use_classification_failed": "No se pudo clasificar el uso propuesto",
        }

        report["final_result"] = {
            "viable": False,
            "error": error_messages.get(reason, "Error desconocido"),
            "summary": f"Validacion incompleta: {error_messages.get(reason)}",
            "recommendations": [
                "1. Verifica que la direccion sea correcta",
                "2. Confirma que el municipio coincida",
                "3. Intenta de nuevo o contacta soporte",
            ],
        }

        report["confidence"] = {
            "overall": 0.0,
            "factors": ["validation_incomplete"],
            "meets_95_percent_target": False,
        }

        return report
