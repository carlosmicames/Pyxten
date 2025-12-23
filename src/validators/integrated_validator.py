"""
Integrated Zoning Validator - Phase 1 Enhanced
Combines: ArcGIS lookup + POT equivalency + NL parsing + Zoning validation
"""

from typing import Dict, List, Optional
from datetime import datetime

from src.utils.arcgis_pr_client import ArcGISPRClient
from src.utils.pot_equivalency import POTEquivalencyTable
from src.ai.use_classifier import UseClassifier
from src.validators.zoning_validator import ZoningValidator
from src.utils.address_validator import AddressValidator


class IntegratedZoningValidator:
    """
    Enhanced validator that:
    1. Takes natural language address + use description
    2. Geocodes address with Google Maps
    3. Queries ArcGIS for zoning + overlays
    4. Handles POT equivalencies
    5. Parses natural language use
    6. Validates compatibility
    7. Returns comprehensive report
    """
    
    def __init__(self, rules_db):
        self.rules_db = rules_db
        self.address_validator = AddressValidator()
        self.arcgis_client = ArcGISPRClient()
        self.pot_table = POTEquivalencyTable()
        
        # Load use types for classifier
        use_types = rules_db.get_use_types()
        self.use_classifier = UseClassifier(use_types)
        
        self.base_validator = ZoningValidator(rules_db)
    
    def validate_from_natural_language(
        self,
        address: str,
        municipality: str,
        use_description: str
    ) -> Dict:
        """
        Main validation method - takes natural language inputs
        
        Args:
            address: "Calle Luna 123, Urb. San Patricio"
            municipality: "San Juan"
            use_description: "quiero construir una residencia con un edificio para una panaderia"
        
        Returns:
            Comprehensive validation report with 95%+ accuracy target
        """
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "input": {
                "address": address,
                "municipality": municipality,
                "use_description": use_description
            },
            "steps": {},
            "final_result": {},
            "confidence": {
                "overall": 0.0,
                "factors": []
            },
            "warnings": [],
            "data_sources": []
        }
        
        # STEP 1: Geocode address
        report["steps"]["1_geocoding"] = self._step_geocode(address, municipality, report)
        if not report["steps"]["1_geocoding"]["success"]:
            return self._early_exit(report, "geocoding_failed")
        
        coords = report["steps"]["1_geocoding"]["coordinates"]
        
        # STEP 2: Query ArcGIS for zoning
        report["steps"]["2_arcgis_lookup"] = self._step_arcgis_lookup(
            coords["latitude"],
            coords["longitude"],
            report
        )
        
        if not report["steps"]["2_arcgis_lookup"]["success"]:
            return self._early_exit(report, "arcgis_failed")
        
        # STEP 3: Handle POT equivalency if needed
        report["steps"]["3_pot_equivalency"] = self._step_pot_equivalency(
            report["steps"]["2_arcgis_lookup"],
            report
        )
        
        # STEP 4: Parse natural language use
        report["steps"]["4_use_classification"] = self._step_classify_use(
            use_description,
            report
        )
        
        if not report["steps"]["4_use_classification"]["uses"]:
            return self._early_exit(report, "use_classification_failed")
        
        # STEP 5: Validate each use against zoning
        report["steps"]["5_compatibility_validation"] = self._step_validate_compatibility(
            report["steps"]["3_pot_equivalency"]["final_zoning_code"],
            report["steps"]["4_use_classification"]["uses"],
            report
        )
        
        # STEP 6: Check overlay restrictions
        report["steps"]["6_overlay_restrictions"] = self._step_check_overlays(
            report["steps"]["2_arcgis_lookup"].get("overlays", []),
            report["steps"]["4_use_classification"]["uses"],
            report
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
            
            if result['valid']:
                report['data_sources'].append({
                    "source": "Google Maps Geocoding API",
                    "purpose": "Address validation and coordinates",
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "success": True,
                    "coordinates": {
                        "latitude": result['latitude'],
                        "longitude": result['longitude']
                    },
                    "formatted_address": result['formatted_address'],
                    "confidence": result['confidence']
                }
            else:
                report['warnings'].append(
                    f"Dirección no validada por Google Maps: {result.get('error')}"
                )
                
                return {
                    "success": False,
                    "error": result.get('error', 'Address validation failed')
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error geocoding: {str(e)}"
            }
    
    def _step_arcgis_lookup(self, lat: float, lon: float, report: Dict) -> Dict:
        """Step 2: Query MIPR ArcGIS for zoning and overlays"""
        
        try:
            property_info = self.arcgis_client.get_complete_property_info(lat, lon)
            
            report['data_sources'].append({
                "source": "MIPR (Mapa Interactivo de Puerto Rico)",
                "purpose": "Zoning district and overlay zones",
                "timestamp": datetime.now().isoformat(),
                "last_updated": property_info['zoning'].get('last_updated'),
                "freshness_warning": property_info.get('data_freshness_warning')
            })
            
            # Add freshness warning
            if property_info.get('data_freshness_warning'):
                report['warnings'].append(property_info['data_freshness_warning'])
            
            if property_info['zoning']['error']:
                return {
                    "success": False,
                    "error": property_info['zoning']['error']
                }
            
            return {
                "success": True,
                "zoning": property_info['zoning'],
                "overlays": property_info.get('overlays', []),
                "municipal_pot": property_info.get('municipal_pot', {}),
                "parcel": property_info.get('parcel'),
                "regulatory_framework": property_info.get('regulatory_framework')
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error querying ArcGIS: {str(e)}"
            }
    
    def _step_pot_equivalency(self, arcgis_result: Dict, report: Dict) -> Dict:
        """Step 3: Handle POT equivalency if municipal POT applies"""
        
        zoning = arcgis_result['zoning']
        district_code = zoning['district_code']
        
        # Check if needs equivalency
        if self.pot_table.is_municipal_specific(district_code):
            # Get RC equivalent
            equivalent = self.pot_table.get_rc_equivalent(district_code, "2020")
            
            if equivalent:
                report['warnings'].append(
                    f"Distrito municipal '{district_code}' mapeado a RC 2020: '{equivalent['rc_code']}'"
                )
                
                report['data_sources'].append({
                    "source": "Tabla 6.1 - Reglamento Conjunto 2023",
                    "purpose": "POT district equivalency mapping",
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "needs_equivalency": True,
                    "original_district": district_code,
                    "original_name": zoning['district_name'],
                    "equivalent": equivalent,
                    "final_zoning_code": equivalent['rc_code'],
                    "final_zoning_name": equivalent['rc_name']
                }
            else:
                report['warnings'].append(
                    f"⚠️ Distrito '{district_code}' no encontrado en tabla de equivalencias"
                )
                
                return {
                    "needs_equivalency": True,
                    "original_district": district_code,
                    "final_zoning_code": district_code,
                    "final_zoning_name": zoning['district_name'],
                    "warning": "Equivalencia no encontrada - usando código original"
                }
        else:
            # Already RC 2020 code
            return {
                "needs_equivalency": False,
                "final_zoning_code": district_code,
                "final_zoning_name": zoning['district_name']
            }
    
    def _step_classify_use(self, use_description: str, report: Dict) -> Dict:
        """Step 4: Parse natural language use description"""
        
        try:
            result = self.use_classifier.parse_natural_language(use_description)
            
            report['data_sources'].append({
                "source": "Claude AI (Anthropic)",
                "purpose": "Natural language use classification",
                "timestamp": datetime.now().isoformat()
            })
            
            # Add clarifications to warnings if needed
            if result.get('clarifications_needed'):
                for clarif in result['clarifications_needed']:
                    report['warnings'].append(f"Clarificación: {clarif}")
            
            return result
        
        except Exception as e:
            return {
                "uses": [],
                "error": f"Error clasificando uso: {str(e)}"
            }
    
    def _step_validate_compatibility(
        self,
        zoning_code: str,
        classified_uses: List[Dict],
        report: Dict
    ) -> Dict:
        """Step 5: Validate each use against zoning"""
        
        validations = []
        
        for use in classified_uses:
            use_code = use['code']
            
            # Use existing validator
            validation_result = self.base_validator.validate_project(
                property_address=report['input']['address'],
                municipality=report['input']['municipality'],
                zoning_code=zoning_code,
                proposed_use_code=use_code
            )
            
            # Add use-specific context
            validation_result['use_interpretation'] = use['interpretation']
            validation_result['use_confidence'] = use['confidence']
            validation_result['use_notes'] = use.get('notes', '')
            
            validations.append(validation_result)
        
        # Determine overall compatibility
        all_viable = all(v['viable'] for v in validations)
        any_ministerial = any(v.get('is_ministerial', False) for v in validations)
        
        return {
            "individual_validations": validations,
            "all_uses_compatible": all_viable,
            "has_ministerial_path": any_ministerial,
            "total_uses_validated": len(validations)
        }
    
    def _step_check_overlays(
        self,
        overlays: List[Dict],
        classified_uses: List[Dict],
        report: Dict
    ) -> Dict:
        """Step 6: Check if overlay zones impose additional restrictions"""
        
        if not overlays:
            return {
                "has_overlays": False,
                "restrictions": []
            }
        
        restrictions = []
        
        for overlay in overlays:
            overlay_type = overlay['overlay_type']
            
            # Check for known restrictions
            if "Histórica" in overlay_type:
                restrictions.append({
                    "overlay": overlay_type,
                    "restriction": "Requiere aprobación del Instituto de Cultura Puertorriqueña (ICP)",
                    "severity": "high",
                    "applies_to": "all_uses"
                })
                
                report['warnings'].append(
                    f"🏛️ Propiedad en Zona Histórica - Requiere aprobación ICP"
                )
            
            if "Costanera" in overlay_type:
                restrictions.append({
                    "overlay": overlay_type,
                    "restriction": "Regulado por Ley de Zona Costanera - Requiere permiso DRNA",
                    "severity": "high",
                    "applies_to": "construction"
                })
                
                report['warnings'].append(
                    f"🌊 Propiedad en Zona Costanera - Restricciones adicionales aplican"
                )
            
            if "Inundación" in overlay_type or "FEMA" in overlay_type:
                restrictions.append({
                    "overlay": overlay_type,
                    "restriction": "Área de riesgo a inundación - Restricciones de construcción",
                    "severity": "high",
                    "applies_to": "construction"
                })
                
                report['warnings'].append(
                    f"⚠️ Área de Riesgo a Inundación - Restricciones especiales"
                )
        
        return {
            "has_overlays": len(overlays) > 0,
            "overlays_detected": overlays,
            "restrictions": restrictions,
            "requires_additional_permits": len(restrictions) > 0
        }
    
    def _generate_final_result(self, report: Dict) -> Dict:
        """Step 7: Generate final determination"""
        
        compatibility = report['steps']['5_compatibility_validation']
        overlays = report['steps']['6_overlay_restrictions']
        uses = report['steps']['4_use_classification']['uses']
        
        # Determine viability
        viable = compatibility['all_uses_compatible']
        
        # Determine permit type
        if viable:
            if overlays['requires_additional_permits']:
                permit_type = "discrecional (overlays)"
            elif compatibility['has_ministerial_path']:
                permit_type = "ministerial"
            else:
                permit_type = "discrecional"
        else:
            permit_type = "no_aplica"
        
        # Generate summary
        if viable:
            if compatibility['all_uses_compatible']:
                summary = f"✅ COMPATIBLE - El uso propuesto es compatible con la zonificación {report['steps']['3_pot_equivalency']['final_zoning_code']}"
            else:
                summary = "⚠️ COMPATIBLE CON RESTRICCIONES - Algunos usos requieren permisos adicionales"
        else:
            summary = f"❌ NO COMPATIBLE - El uso propuesto no es permitido en zonificación {report['steps']['3_pot_equivalency']['final_zoning_code']}"
        
        # Generate recommendations
        recommendations = []
        
        if viable:
            if permit_type == "ministerial":
                recommendations.append("1. Preparar documentos para Permiso Único")
                recommendations.append("2. Contratar Profesional Autorizado (PA)")
                recommendations.append("3. Someter solicitud a OGPe o municipio")
            else:
                recommendations.append("1. Solicitar Consulta de Ubicación (CUB)")
                recommendations.append("2. Preparar estudios técnicos requeridos")
                recommendations.append("3. Coordinar con agencias concernidas")
        else:
            recommendations.append("1. Considerar cambio de zonificación (rezoning)")
            recommendations.append("2. Modificar uso propuesto")
            recommendations.append("3. Buscar propiedad en zonificación compatible")
        
        # Add overlay-specific recommendations
        if overlays['requires_additional_permits']:
            for restriction in overlays['restrictions']:
                recommendations.append(f"• {restriction['restriction']}")
        
        return {
            "viable": viable,
            "permit_type": permit_type,
            "summary": summary,
            "uses_validated": uses,
            "total_uses": len(uses),
            "mixed_use": len(uses) > 1,
            "recommendations": recommendations,
            "next_steps": self._generate_next_steps(viable, permit_type, overlays)
        }
    
    def _generate_next_steps(self, viable: bool, permit_type: str, overlays: Dict) -> List[str]:
        """Generate actionable next steps"""
        
        steps = []
        
        if viable:
            steps.append("✅ Paso 1: Validación preliminar COMPLETADA")
            
            if permit_type == "ministerial":
                steps.append("📄 Paso 2: Preparar documentación (planos, certificaciones)")
                steps.append("👷 Paso 3: Contratar Profesional Autorizado (PA)")
                steps.append("📤 Paso 4: Someter solicitud de Permiso Único")
                steps.append("⏱️ Tiempo estimado: 1-3 meses")
            else:
                steps.append("📋 Paso 2: Solicitar Consulta de Ubicación (CUB)")
                steps.append("📊 Paso 3: Preparar estudios técnicos")
                
                if overlays['requires_additional_permits']:
                    steps.append("🏛️ Paso 4: Obtener permisos de agencias concernidas")
                
                steps.append("⏱️ Tiempo estimado: 4-8 meses")
        else:
            steps.append("❌ Proyecto NO VIABLE en ubicación actual")
            steps.append("🔄 Opción 1: Solicitar cambio de zonificación")
            steps.append("📍 Opción 2: Buscar propiedad en zona compatible")
            steps.append("✏️ Opción 3: Modificar uso propuesto")
        
        return steps
    
    def _calculate_confidence(self, report: Dict) -> Dict:
        """Calculate overall confidence score"""
        
        factors = []
        scores = []
        
        # Geocoding confidence
        geocode = report['steps']['1_geocoding']
        if geocode.get('confidence') == 'ROOFTOP':
            factors.append("address_exact")
            scores.append(1.0)
        elif geocode.get('success'):
            factors.append("address_approximate")
            scores.append(0.8)
        
        # ArcGIS data confidence
        arcgis = report['steps']['2_arcgis_lookup']
        if arcgis['zoning']['confidence'] == 'high':
            factors.append("zoning_confirmed")
            scores.append(1.0)
        else:
            factors.append("zoning_uncertain")
            scores.append(0.6)
        
        # Use classification confidence
        use_class = report['steps']['4_use_classification']
        if use_class.get('uses'):
            avg_use_confidence = sum(u['confidence'] for u in use_class['uses']) / len(use_class['uses'])
            factors.append("use_classified")
            scores.append(avg_use_confidence)
        
        # Overlay detection
        overlays = report['steps']['6_overlay_restrictions']
        if overlays['has_overlays']:
            factors.append("overlays_detected")
            scores.append(0.9)  # Slight confidence reduction due to complexity
        else:
            factors.append("no_overlays")
            scores.append(1.0)
        
        # Calculate overall
        overall = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "overall": overall,
            "factors": factors,
            "breakdown": {
                "geocoding": scores[0] if len(scores) > 0 else 0,
                "zoning_data": scores[1] if len(scores) > 1 else 0,
                "use_classification": scores[2] if len(scores) > 2 else 0
            },
            "meets_95_percent_target": overall >= 0.95
        }
    
    def _early_exit(self, report: Dict, reason: str) -> Dict:
        """Handle early exit with error"""
        
        error_messages = {
            "geocoding_failed": "No se pudo validar la dirección",
            "arcgis_failed": "No se pudo obtener información de zonificación",
            "use_classification_failed": "No se pudo clasificar el uso propuesto"
        }
        
        report['final_result'] = {
            "viable": False,
            "error": error_messages.get(reason, "Error desconocido"),
            "summary": f"❌ Validación incompleta: {error_messages.get(reason)}",
            "recommendations": [
                "1. Verifica que la dirección sea correcta",
                "2. Confirma que el municipio coincida",
                "3. Intenta de nuevo o contacta soporte"
            ]
        }
        
        report['confidence'] = {
            "overall": 0.0,
            "factors": ["validation_incomplete"],
            "meets_95_percent_target": False
        }
        
        return report


# Example usage
if __name__ == "__main__":
    from src.database.rules_loader import RulesDatabase
    
    rules_db = RulesDatabase()
    validator = IntegratedZoningValidator(rules_db)
    
    # Test case
    result = validator.validate_from_natural_language(
        address="Calle del Cristo 255",
        municipality="San Juan",
        use_description="quiero operar un hotel boutique con restaurante"
    )
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))