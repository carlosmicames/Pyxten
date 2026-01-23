"""
Phase 1 Validation Service
Ported from src/validators/integrated_validator.py
"""

from datetime import datetime
from typing import Dict, List

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
    2. ArcGIS lookup for parcel + overlays (NOT zoning district; user provides district_code)
    3. POT equivalencies (municipal POT -> RC mapping)
    4. Natural language use classification
    5. Zoning compatibility validation
    6. Overlay restrictions (optional but recommended)
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
        district_code: str,
    ) -> Dict:
        """
        Main validation method

        Args:
            address: Property address
            municipality: Municipality name
            project_description: Natural language description of intended use
            district_code: User-selected zoning district code (required)

        Returns:
            Comprehensive validation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "input": {
                "address": address,
                "municipality": municipality,
                "project_description": project_description,
                "district_code": district_code,
            },
            "steps": {},
            "final_result": {},
            "confidence": {"overall": 0.0, "factors": []},
            "warnings": [],
            "data_sources": [],
        }

        # STEP 1: Geocode address
        report["steps"]["1_geocoding"] = self._step_geocode(address, municipality, report)
        if not report["steps"]["1_geocoding"].get("success", False):
            return self._early_exit(report, "geocoding_failed")

        coords = report["steps"]["1_geocoding"]["coordinates"]

        # STEP 2: Query ArcGIS for parcel + overlays (NOT zoning - user provides district)
        report["steps"]["2_arcgis_lookup"] = self._step_arcgis_parcel_overlays(
            coords["latitude"], coords["longitude"], report
        )

        # STEP 3: Handle POT equivalency using user-provided district_code
        report["steps"]["3_pot_equivalency"] = self._step_pot_equivalency_from_user(
            district_code, municipality, report
        )

        # STEP 4: Parse natural language use
        report["steps"]["4_use_classification"] = self._step_classify_use(project_description, report)

        if not report["steps"]["4_use_classification"].get("uses"):
            return self._early_exit(report, "use_classification_failed")

        # STEP 5: Validate each use against zoning
        final_zoning_code = report["steps"]["3_pot_equivalency"].get("final_zoning_code", "")
        report["steps"]["5_compatibility_validation"] = self._step_validate_compatibility(
            final_zoning_code,
            report["steps"]["4_use_classification"]["uses"],
            report,
        )

        # STEP 6: Check overlay restrictions
        overlays_list = report["steps"]["2_arcgis_lookup"].get("overlays", []) or []
        report["steps"]["6_overlay_restrictions"] = self._step_check_overlays(
            overlays_list,
            report["steps"]["4_use_classification"]["uses"],
            report,
        )

        # STEP 7: Generate final determination
        report["final_result"] = self._generate_final_result(report)

        # Calculate overall confidence
        report["confidence"] = self._calculate_confidence(report)

        return report

    # -------------------------------------------------------------------------
    # Step 1
    # -------------------------------------------------------------------------
    def _step_geocode(self, address: str, municipality: str, report: Dict) -> Dict:
        """Step 1: Geocode address with Google Maps"""
        try:
            result = self.address_validator.validate_address(address, municipality)

            if result.get("valid"):
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
                        "latitude": result.get("latitude"),
                        "longitude": result.get("longitude"),
                    },
                    "formatted_address": result.get("formatted_address"),
                    "confidence": result.get("confidence"),
                }

            report["warnings"].append(f"Direccion no validada: {result.get('error')}")
            return {"success": False, "error": result.get("error", "Address validation failed")}

        except Exception as e:
            return {"success": False, "error": f"Error geocoding: {str(e)}"}

    # -------------------------------------------------------------------------
    # Step 2
    # -------------------------------------------------------------------------
    def _step_arcgis_parcel_overlays(self, lat: float, lon: float, report: Dict) -> Dict:
        """Step 2: Query ArcGIS for parcel info and overlays (NOT zoning - user provides district)"""
        try:
            parcel_result = self.arcgis_client.get_parcel_info(lat, lon)
            overlay_result = self.arcgis_client.get_overlay_zones(lat, lon)

            report["data_sources"].append(
                {
                    "source": "ArcGIS CRIM / MIPR",
                    "purpose": "Parcel info and overlay zones",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return {
                "success": True,
                "parcel": parcel_result if parcel_result and parcel_result.get("success") else None,
                "overlays": (overlay_result or {}).get("overlays", []) or [],
            }

        except Exception as e:
            # Non-fatal - ArcGIS issues shouldn't block zoning compatibility
            report["warnings"].append(f"Error consultando ArcGIS: {str(e)}")
            return {"success": True, "parcel": None, "overlays": []}

    # -------------------------------------------------------------------------
    # Step 3
    # -------------------------------------------------------------------------
    def _step_pot_equivalency_from_user(self, district_code: str, municipality: str, report: Dict) -> Dict:
        """Step 3: Handle POT equivalency using user-provided district code"""
        normalized = (district_code or "").strip().upper()

        if not normalized:
            report["warnings"].append("No se recibio district_code (zonificacion) del usuario.")
            return {
                "needs_equivalency": False,
                "user_selected_district": "",
                "final_zoning_code": "",
                "final_zoning_name": "",
                "warning": "Zonificacion requerida no provista",
            }

        # POT municipal codes (municipal-specific) -> map to RC if possible
        if self.pot_table.is_municipal_specific(normalized):
            equivalent = self.pot_table.get_rc_equivalent(normalized, "2020")

            report["data_sources"].append(
                {
                    "source": "Tabla 6.1 - Reglamento Conjunto 2023",
                    "purpose": "POT district equivalency mapping",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if equivalent:
                report["warnings"].append(
                    f"Distrito municipal '{normalized}' mapeado a RC 2020: '{equivalent['rc_code']}'"
                )
                return {
                    "needs_equivalency": True,
                    "user_selected_district": normalized,
                    "equivalent": equivalent,
                    "final_zoning_code": equivalent["rc_code"],
                    "final_zoning_name": equivalent.get("rc_name", equivalent["rc_code"]),
                }

            # No mapping found — keep original
            report["warnings"].append(
                f"Distrito '{normalized}' no encontrado en tabla de equivalencias - usando codigo original"
            )
            return {
                "needs_equivalency": True,
                "user_selected_district": normalized,
                "final_zoning_code": normalized,
                "final_zoning_name": normalized,
                "warning": "Equivalencia no encontrada - usando codigo original",
            }

        # Already RC / joint regulation code
        return {
            "needs_equivalency": False,
            "user_selected_district": normalized,
            "final_zoning_code": normalized,
            "final_zoning_name": normalized,
        }

    # -------------------------------------------------------------------------
    # Step 4
    # -------------------------------------------------------------------------
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
            return {"uses": [], "error": f"Error clasificando uso: {str(e)}"}

    # -------------------------------------------------------------------------
    # Step 5
    # -------------------------------------------------------------------------
    def _step_validate_compatibility(self, zoning_code: str, classified_uses: List[Dict], report: Dict) -> Dict:
        """Step 5: Validate each use against zoning"""
        validations = []

        for use in classified_uses:
            use_code = use.get("code")
            if not use_code:
                validations.append({"use_code": None, "viable": False, "error": "Uso sin 'code'."})
                continue

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

            compatible_zones = use_type.get("compatible_zones", []) or []
            is_compatible = zoning_code in compatible_zones
            is_ministerial = bool(is_compatible and use_type.get("ministerial", False))

            validations.append(
                {
                    "use_code": use_code,
                    "use_name": use_type.get("name_es", use_code),
                    "viable": is_compatible,
                    "is_ministerial": is_ministerial,
                    "zoning_code": zoning_code,
                    "compatible_zones": compatible_zones,
                    "use_interpretation": use.get("interpretation", ""),
                    "use_confidence": use.get("confidence", 0.5),
                    "message": self._get_compatibility_message(is_compatible, zoning_code, use_type),
                }
            )

        all_viable = all(v.get("viable", False) for v in validations) if validations else False
        any_ministerial = any(v.get("is_ministerial", False) for v in validations)

        return {
            "individual_validations": validations,
            "all_uses_compatible": all_viable,
            "has_ministerial_path": any_ministerial,
            "total_uses_validated": len(validations),
        }

    def _get_compatibility_message(self, is_compatible: bool, zoning_code: str, use_type: Dict) -> str:
        """Generate compatibility validation message"""
        use_name = use_type.get("name_es", "uso")
        if is_compatible:
            return f"El uso '{use_name}' ES COMPATIBLE con la zonificacion {zoning_code}"

        compatible_list = ", ".join(use_type.get("compatible_zones", []) or [])
        return (
            f"El uso '{use_name}' NO ES COMPATIBLE con la zonificacion {zoning_code}. "
            f"Este uso solo se permite en: {compatible_list}"
        )

    # -------------------------------------------------------------------------
    # Step 6
    # -------------------------------------------------------------------------
    def _step_check_overlays(self, overlays: List[Dict], classified_uses: List[Dict], report: Dict) -> Dict:
        """
        Step 6: Check if overlay zones impose additional restrictions.

        IMPORTANT:
        Always return a dict with consistent keys so downstream steps never KeyError.
        """
        # Normalize output shape (always)
        result = {
            "has_overlays": bool(overlays),
            "overlays_detected": overlays or [],
            "restrictions": [],
            "requires_additional_permits": False,
        }

        if not overlays:
            return result

        restrictions = []

        for overlay in overlays:
            overlay_type = (overlay.get("type") or overlay.get("overlay_type") or "").strip()

            # Guard: skip unknown overlay entries
            if not overlay_type:
                continue

            low = overlay_type.lower()

            if "historica" in low:
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Requiere aprobacion del Instituto de Cultura Puertorriquena (ICP)",
                        "severity": "high",
                    }
                )
                report["warnings"].append("Propiedad en Zona Historica - Requiere aprobacion ICP")

            if "costanera" in low:
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Regulado por Ley de Zona Costanera - Requiere permiso DRNA",
                        "severity": "high",
                    }
                )
                report["warnings"].append("Propiedad en Zona Costanera - Restricciones adicionales aplican")

            if "inundacion" in low or "fema" in low:
                restrictions.append(
                    {
                        "overlay": overlay_type,
                        "restriction": "Area de riesgo a inundacion - Restricciones de construccion",
                        "severity": "high",
                    }
                )
                report["warnings"].append("Area de Riesgo a Inundacion - Restricciones especiales")

        result["restrictions"] = restrictions
        result["requires_additional_permits"] = len(restrictions) > 0
        return result

    # -------------------------------------------------------------------------
    # Step 7
    # -------------------------------------------------------------------------
    def _generate_final_result(self, report: Dict) -> Dict:
        """Step 7: Generate final determination"""
        compatibility = report["steps"].get("5_compatibility_validation", {}) or {}
        overlays = report["steps"].get("6_overlay_restrictions", {}) or {}
        uses = (report["steps"].get("4_use_classification", {}) or {}).get("uses", []) or []

        zoning_code = (report["steps"].get("3_pot_equivalency", {}) or {}).get("final_zoning_code", "")
        zoning_name = (report["steps"].get("3_pot_equivalency", {}) or {}).get("final_zoning_name", zoning_code)

        viable = bool(compatibility.get("all_uses_compatible", False))

        requires_overlay_permits = overlays.get("requires_additional_permits", False)
        has_ministerial = bool(compatibility.get("has_ministerial_path", False))

        # Decide permit type
        if not viable:
            permit_type = "no_aplica"
        else:
            if requires_overlay_permits:
                permit_type = "discrecional (overlays)"
            elif has_ministerial:
                permit_type = "ministerial"
            else:
                permit_type = "discrecional"

        # Summary
        if viable:
            summary = f"COMPATIBLE - El uso propuesto es compatible con la zonificacion {zoning_code}"
        else:
            summary = f"NO COMPATIBLE - El uso propuesto no es permitido en zonificacion {zoning_code}"

        # Recommendations
        recommendations = []

        if viable:
            if permit_type == "ministerial":
                recommendations.extend(
                    [
                        "1. Preparar documentos para Permiso Unico",
                        "2. Contratar Profesional Autorizado (PA)",
                        "3. Someter solicitud a OGPe o municipio",
                    ]
                )
            else:
                recommendations.extend(
                    [
                        "1. Solicitar Consulta de Ubicacion (CUB) (si aplica)",
                        "2. Preparar estudios tecnicos requeridos",
                        "3. Coordinar con agencias concernidas",
                    ]
                )
        else:
            recommendations.extend(
                [
                    "1. Considerar cambio de zonificacion (rezoning)",
                    "2. Modificar uso propuesto",
                    "3. Buscar propiedad en zonificacion compatible",
                ]
            )

        # Overlay restrictions appended
        if requires_overlay_permits:
            for restriction in overlays.get("restrictions", []) or []:
                rtxt = restriction.get("restriction")
                if rtxt:
                    recommendations.append(f"- {rtxt}")

        return {
            "viable": viable,
            "permit_type": permit_type,
            "summary": summary,
            "uses_validated": uses,
            "total_uses": len(uses),
            "mixed_use": len(uses) > 1,
            "recommendations": recommendations,
            "zoning_code": zoning_code,
            "zoning_name": zoning_name,
            "overlays_apply": bool(overlays.get("has_overlays", False)),
        }

    # -------------------------------------------------------------------------
    # Confidence
    # -------------------------------------------------------------------------
    def _calculate_confidence(self, report: Dict) -> Dict:
        """Calculate overall confidence score"""
        factors = []
        scores = []

        geocode = report["steps"].get("1_geocoding", {}) or {}
        if geocode.get("confidence") == "ROOFTOP":
            factors.append("address_exact")
            scores.append(1.0)
        elif geocode.get("success"):
            factors.append("address_approximate")
            scores.append(0.8)

        pot_equiv = report["steps"].get("3_pot_equivalency", {}) or {}
        if pot_equiv.get("final_zoning_code"):
            factors.append("zoning_user_provided")
            scores.append(1.0)
        else:
            factors.append("zoning_missing")
            scores.append(0.5)

        use_class = report["steps"].get("4_use_classification", {}) or {}
        uses = use_class.get("uses", []) or []
        if uses:
            avg_use_conf = sum(u.get("confidence", 0.5) for u in uses) / len(uses)
            factors.append("use_classified")
            scores.append(avg_use_conf)

        overlays = report["steps"].get("6_overlay_restrictions", {}) or {}
        if overlays.get("has_overlays", False):
            factors.append("overlays_detected")
            # Slightly lower confidence because overlays can introduce complexity
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

    # -------------------------------------------------------------------------
    # Early exit
    # -------------------------------------------------------------------------
    def _early_exit(self, report: Dict, reason: str) -> Dict:
        """Handle early exit with error"""
        error_messages = {
            "geocoding_failed": "No se pudo validar la direccion",
            "use_classification_failed": "No se pudo clasificar el uso propuesto",
        }

        msg = error_messages.get(reason, "Error desconocido")

        report["final_result"] = {
            "viable": False,
            "error": msg,
            "summary": f"Validacion incompleta: {msg}",
            "recommendations": [
                "1. Verifica que la direccion sea correcta",
                "2. Confirma que el municipio coincida",
                "3. Intenta de nuevo o contacta soporte",
            ],
        }

        report["confidence"] = {"overall": 0.0, "factors": ["validation_incomplete"], "meets_95_percent_target": False}
        return report
