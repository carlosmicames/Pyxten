#Core Validation Logic
from typing import Dict, List, Tuple
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
        proposed_use_code: str
    ) -> Dict:
        """
        Main validation function - checks project against Tomo 6 rules
        
        Returns:
            Dict with validation results and viability assessment
        """
        # Reset results
        self.validation_results = []
        
        # Get zoning and use data
        zoning_district = self.rules_db.get_zoning_district(zoning_code)
        proposed_use = self.rules_db.get_use_type(proposed_use_code)
        
        if not zoning_district:
            return {
                "viable": False,
                "error": f"Distrito de zonificación '{zoning_code}' no encontrado"
            }
        
        if not proposed_use:
            return {
                "viable": False,
                "error": f"Tipo de uso '{proposed_use_code}' no encontrado"
            }
        
        # Run validations
        self._validate_use_compatibility(zoning_district, proposed_use)
        
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
                "code": zoning_district["code"],
                "name": zoning_district["name_es"]
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
    
    def _validate_use_compatibility(
        self,
        zoning_district: Dict,
        proposed_use: Dict
    ):
        """Rule T6-001: Validate use is compatible with zoning"""
        
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
                f"✓ El uso '{use['name_es']}' ES COMPATIBLE con la zonificación "
                f"{zoning['code']} ({zoning['name_es']})"
            )
        else:
            compatible_list = ", ".join(use.get("compatible_zones", []))
            return (
                f"✗ El uso '{use['name_es']}' NO ES COMPATIBLE con la zonificación "
                f"{zoning['code']}. Este uso solo se permite en: {compatible_list}"
            )
    
    def _generate_summary(self, viable: bool, ministerial: bool) -> str:
        """Generate validation summary"""
        
        if not viable:
            return (
                "❌ PROYECTO NO VIABLE - El uso propuesto no es compatible con "
                "la zonificación. Se requieren cambios significativos."
            )
        
        if ministerial:
            return (
                "✅ PROYECTO VIABLE - Permiso MINISTERIAL. El proyecto cumple con "
                "todos los requisitos de Tomo 6 y califica para tramitación expedita."
            )
        else:
            return (
                "⚠️ PROYECTO VIABLE CON CONDICIONES - El uso es compatible pero "
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
