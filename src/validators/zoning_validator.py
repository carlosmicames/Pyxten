#Core Validation Logic
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class ZoningValidator:
    """Validates zoning compliance according to Tomo 6"""

    def __init__(self, rules_db):
        self.rules_db = rules_db
        self.validation_results = []

    def validate_project(
        self,
        property_address: str,
        municipality: str,
        zoning_code: str,
        proposed_use_code: str,
        rc_equivalents: Optional[List[str]] = None
    ) -> Dict:
        """
        Main validation function - checks project against Tomo 6 rules

        Args:
            property_address: Address of the property
            municipality: Municipality name
            zoning_code: The POT or RC zoning code
            proposed_use_code: The proposed use code
            rc_equivalents: Optional list of RC equivalent codes for POT zones

        Returns:
            Dict with validation results and viability assessment
        """
        # Reset results
        self.validation_results = []

        # If rc_equivalents not provided, use zoning_code as single equivalent
        if rc_equivalents is None:
            rc_equivalents = [zoning_code]

        # Get use data
        proposed_use = self.rules_db.get_use_type(proposed_use_code)

        if not proposed_use:
            return {
                "viable": False,
                "error": f"Tipo de uso '{proposed_use_code}' no encontrado"
            }

        # Validate against ALL RC equivalents - viable if ANY match
        compatible_with = []
        all_zoning_districts = []

        for rc_code in rc_equivalents:
            zoning_district = self.rules_db.get_zoning_district(rc_code)
            if zoning_district:
                all_zoning_districts.append(zoning_district)
                compatible_zones = proposed_use.get("compatible_zones", [])
                if rc_code in compatible_zones:
                    compatible_with.append(rc_code)

        # Use first valid zoning district for display
        primary_zoning = all_zoning_districts[0] if all_zoning_districts else None

        if not primary_zoning:
            return {
                "viable": False,
                "error": f"Ninguno de los distritos de zonificación encontrados: {rc_equivalents}"
            }

        # Run validations with multi-equivalence support
        self._validate_use_compatibility_multi(
            zoning_code=zoning_code,
            rc_equivalents=rc_equivalents,
            proposed_use=proposed_use,
            compatible_with=compatible_with
        )

        # Compile results
        all_critical_passed = all(
            r["passed"] for r in self.validation_results
            if r.get("critical", False)
        )

        is_ministerial = all_critical_passed and proposed_use.get("ministerial", False)

        return {
            "viable": all_critical_passed,
            "is_ministerial": is_ministerial,
            "property_address": property_address,
            "municipality": municipality,
            "zoning_district": {
                "code": zoning_code,
                "name": primary_zoning["name_es"],
                "rc_equivalents": rc_equivalents,
                "compatible_with": compatible_with
            },
            "proposed_use": {
                "code": proposed_use["code"],
                "name": proposed_use["name_es"]
            },
            "validation_results": self.validation_results,
            "summary": self._generate_summary(all_critical_passed, is_ministerial),
            "next_steps": self._generate_next_steps(all_critical_passed, is_ministerial),
            "validated_at": datetime.now().isoformat()
        }
    
    def _validate_use_compatibility_multi(
        self,
        zoning_code: str,
        rc_equivalents: List[str],
        proposed_use: Dict,
        compatible_with: List[str]
    ):
        """
        Rule T6-001: Validate use is compatible with zoning.
        For POT codes with multiple RC equivalents, validates against ALL and
        passes if compatible with AT LEAST ONE.
        """
        compatible_zones = proposed_use.get("compatible_zones", [])
        is_compatible = len(compatible_with) > 0

        if is_compatible:
            message = (
                f"El uso '{proposed_use['name_es']}' ES COMPATIBLE con la zonificación "
                f"{zoning_code}. Compatible con: {', '.join(compatible_with)}"
            )
        else:
            message = (
                f"El uso '{proposed_use['name_es']}' NO ES COMPATIBLE con ninguna de las "
                f"equivalencias RC de {zoning_code}: {', '.join(rc_equivalents)}. "
                f"Este uso solo se permite en: {', '.join(compatible_zones[:5])}{'...' if len(compatible_zones) > 5 else ''}"
            )

        result = {
            "rule_id": "T6-001",
            "rule_name": "Compatibilidad de Uso y Zonificación",
            "article": "Reglamento Conjunto, Tomo 6, Artículo 6.1",
            "passed": is_compatible,
            "critical": True,
            "message": message,
            "details": {
                "zoning_code": zoning_code,
                "rc_equivalents": rc_equivalents,
                "compatible_with": compatible_with,
                "use_category": proposed_use.get("category"),
                "all_compatible_zones": compatible_zones
            }
        }

        self.validation_results.append(result)

    def _validate_use_compatibility(
        self,
        zoning_district: Dict,
        proposed_use: Dict
    ):
        """Rule T6-001: Validate use is compatible with zoning (legacy single-zone method)"""

        compatible_zones = proposed_use.get("compatible_zones", [])
        is_compatible = zoning_district["code"] in compatible_zones

        result = {
            "rule_id": "T6-001",
            "rule_name": "Compatibilidad de Uso y Zonificación",
            "article": "Reglamento Conjunto, Tomo 6, Artículo 6.1",
            "passed": is_compatible,
            "critical": True,
            "message": self._get_compatibility_message(
                is_compatible,
                zoning_district,
                proposed_use
            ),
            "details": {
                "zoning_category": zoning_district.get("category"),
                "use_category": proposed_use.get("category"),
                "compatible_zones": compatible_zones
            }
        }

        self.validation_results.append(result)
    
    def _get_compatibility_message(
        self,
        is_compatible: bool,
        zoning: Dict,
        use: Dict
    ) -> str:
        """Generate compatibility validation message"""
        
        if is_compatible:
            return (
                f"El uso '{use['name_es']}' ES COMPATIBLE con la zonificación "
                f"{zoning['code']} ({zoning['name_es']})"
            )
        else:
            compatible_list = ", ".join(use.get("compatible_zones", []))
            return (
                f"El uso '{use['name_es']}' NO ES COMPATIBLE con la zonificación "
                f"{zoning['code']}. Este uso solo se permite en: {compatible_list}"
            )
    
    def _generate_summary(self, viable: bool, ministerial: bool) -> str:
        """Generate validation summary"""
        
        if not viable:
            return (
                "PROYECTO NO VIABLE - El uso propuesto no es compatible con "
                "la zonificación. Se requieren cambios significativos."
            )
        
        if ministerial:
            return (
                "PROYECTO VIABLE - Permiso MINISTERIAL. El proyecto cumple con "
                "todos los requisitos de Tomo 6 y califica para tramitación expedita."
            )
        else:
            return (
                "PROYECTO VIABLE CON CONDICIONES - El uso es compatible pero "
                "requiere proceso DISCRECIONAL. Se necesitarán permisos adicionales."
            )
    
    def _generate_next_steps(self, viable: bool, ministerial: bool) -> List[str]:
        """Generate recommended next steps"""
        
        if not viable:
            return [
                "1. Solicitar rezoning de la propiedad",
                "2. Buscar propiedad en zonificación compatible",
                "3. Modificar el uso propuesto para que sea compatible"
            ]
        
        if ministerial:
            return [
                "1. Preparar documentos requeridos (escritura, planos, certificaciones)",
                "2. Contratar Profesional Autorizado (PA) si aplica",
                "3. Someter solicitud de Permiso Único o PCOC según corresponda",
                "4. Esperar validación (típicamente 1-5 días hábiles)"
            ]
        else:
            return [
                "1. Solicitar Consulta de Ubicación (CUB) a la Junta de Planificación",
                "2. Preparar documentos técnicos (estudios de impacto, traffic, etc.)",
                "3. Coordinar con agencias concernidas",
                "4. Anticipar proceso de 4-8 meses para aprobación"
            ]
