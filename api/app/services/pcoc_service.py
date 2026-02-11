"""
PCOC Validation Service
Business logic for construction permit validation checklist
"""
from typing import Dict, List, Any, Optional
from app.services.rules_data import get_rules_db


# =============================================================================
# EXEMPT WORK CATEGORIES (Sec 3.2.4 del RC)
# =============================================================================

EXEMPT_WORK_CATEGORIES = [
    {
        "code": "EXC-01",
        "name_es": "Pintura de edificios o estructuras existentes",
        "name_en": "Painting of existing buildings or structures",
        "section": "3.2.4",
    },
    {
        "code": "EXC-02",
        "name_es": "Sellado de techos",
        "name_en": "Roof sealing",
        "section": "3.2.4",
    },
    {
        "code": "EXC-03",
        "name_es": "Trabajos de jardineria",
        "name_en": "Landscaping work",
        "section": "3.2.4",
    },
    {
        "code": "EXC-04",
        "name_es": "Relleno de grietas, salideros y goteras",
        "name_en": "Filling cracks, leaks and drips",
        "section": "3.2.4",
    },
    {
        "code": "EXC-05",
        "name_es": "Enlucido (empañetado) de obras de hormigon existente",
        "name_en": "Plastering of existing concrete structures",
        "section": "3.2.4",
    },
    {
        "code": "EXC-06",
        "name_es": "Instalacion o cambios de losetas de piso, azulejos, ceramica, o terminacion de piso o pared",
        "name_en": "Installation or changes of floor tiles, ceramic, or floor/wall finishes",
        "section": "3.2.4",
    },
    {
        "code": "EXC-07",
        "name_es": "Instalacion de acusticos y luminarias",
        "name_en": "Installation of acoustic panels and lighting fixtures",
        "section": "3.2.4",
    },
    {
        "code": "EXC-08",
        "name_es": "Instalacion, cambios o sustitucion de puertas, ventanas o vitrinas",
        "name_en": "Installation, changes or replacement of doors, windows or display cases",
        "section": "3.2.4",
    },
    {
        "code": "EXC-09",
        "name_es": "Instalacion de equipos o su relocalizacion (sin elementos estructurales, mecanicos, plomeria o electrica)",
        "name_en": "Equipment installation or relocation (without structural, mechanical, plumbing or electrical elements)",
        "section": "3.2.4",
    },
    {
        "code": "EXC-10",
        "name_es": "Instalacion de equipos de cocinas y baños (sin elementos estructurales, mecanicos, plomeria o electrica)",
        "name_en": "Kitchen and bathroom equipment installation (without structural, mechanical, plumbing or electrical)",
        "section": "3.2.4",
    },
    {
        "code": "EXC-11",
        "name_es": "Instalacion de paredes de gypsum board y materiales similares (sin elementos estructurales, mecanicos, plomeria o electrica)",
        "name_en": "Installation of gypsum board walls (without structural, mechanical, plumbing or electrical)",
        "section": "3.2.4",
    },
    {
        "code": "EXC-12",
        "name_es": "Instalacion de rejas, verjas en cyclone fence, PVC, metal (sin elementos estructurales)",
        "name_en": "Installation of fences in cyclone fence, PVC, metal (without structural elements)",
        "section": "3.2.4",
    },
    {
        "code": "EXC-13",
        "name_es": "Asfaltar calles, caminos o estacionamientos existentes",
        "name_en": "Asphalting existing streets, roads or parking lots",
        "section": "3.2.4",
    },
]

# Minor work exemptions (Sec 3.2.4.2)
MINOR_WORK_EXEMPTIONS = [
    {
        "code": "MIN-01",
        "name_es": "Construccion cuya elevacion no excede 1 metro desde nivel natural del terreno (sin riesgo estructural, sin vigas, varillas, columnas, aleros)",
        "name_en": "Construction not exceeding 1 meter elevation from ground level (no structural risk, no beams, rebar, columns, eaves)",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-02",
        "name_es": "Verjas conforme a la Regla 8.3.2",
        "name_en": "Fences conforming to Rule 8.3.2",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-03",
        "name_es": "Construccion o cambio de divisiones interiores (sin crear unidades adicionales, sin afectar salidas, elementos estructurales o sistemas principales)",
        "name_en": "Interior division construction/changes (no additional units, no exit/structural/system impact)",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-04",
        "name_es": "Sustitucion de material viejo por nuevo de igual clase (madera por madera, zinc por zinc, etc.)",
        "name_en": "Replacement of old material with same type (wood for wood, zinc for zinc, etc.)",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-05",
        "name_es": "Instalacion de cables, fibra optica o tuberias para telecomunicaciones en servidumbres existentes",
        "name_en": "Installation of cables, fiber optic or telecom pipes in existing easements",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-06",
        "name_es": "Instalacion de estructuras removibles para usos agricolas con conexiones existentes",
        "name_en": "Installation of removable structures for agricultural use with existing connections",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-07",
        "name_es": "Cambios arquitectonicos en fachadas (sin alteraciones estructurales)",
        "name_en": "Architectural facade changes (without structural alterations)",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-08",
        "name_es": "Sustituciones sencillas en sistemas de plomeria, electrica o telecomunicaciones (solo cambio o sustitucion de equipo, tubos o aditamentos nuevos)",
        "name_en": "Simple substitutions in plumbing, electrical or telecom systems (equipment/tube/fitting replacement only)",
        "section": "3.2.4.2",
    },
    {
        "code": "MIN-09",
        "name_es": "Sustituciones sencillas en rotulos y anuncios (partes removibles o pintura de rotulo conforme)",
        "name_en": "Simple sign substitutions (removable parts or compliant sign painting)",
        "section": "3.2.4.2",
    },
]

# Categorical Exclusions (OA 2025-10 DRNA)
# Full list from Administrative Order 2025-10
CATEGORICAL_EXCLUSIONS_OA_2025_10 = [
    # A. General Actions
    {
        "code": "CE-A1",
        "category": "A",
        "name_es": "Acciones declaradas como EXC por leyes especiales, reglamentos, ordenes administrativas del DRNA u ordenes ejecutivas",
        "name_en": "Actions declared as CEs by special laws, regulations, administrative orders of DRNA, or executive orders",
    },
    {
        "code": "CE-A2",
        "category": "A",
        "name_es": "Proyectos aprobados como EXC por agencias del gobierno federal",
        "name_en": "Projects approved as CEs by federal government agencies",
    },
    {
        "code": "CE-A3",
        "category": "A",
        "name_es": "Proyectos criticos evaluados y aprobados bajo la Ley PROMESA",
        "name_en": "Critical projects evaluated and approved under the PROMESA Act",
    },
    {
        "code": "CE-A4",
        "category": "A",
        "name_es": "Obras relacionadas con la reparacion, reconstruccion, demolicion o instalacion de infraestructura directamente vinculada a una emergencia o desastre declarado",
        "name_en": "Works related to repair, reconstruction, demolition, or installation of infrastructure directly linked to a declared emergency or disaster",
    },
    {
        "code": "CE-A5",
        "category": "A",
        "name_es": "Proyectos de estudios, planificacion, pruebas, analisis tecnicos o procedimientos administrativos que no impliquen intervencion fisica directa sobre el ambiente",
        "name_en": "Projects consisting of studies, planning, tests, technical analysis, or administrative procedures without direct physical intervention on the environment",
    },
    {
        "code": "CE-A6",
        "category": "A",
        "name_es": "Adopcion o aprobacion de programas, planes y reglamentos (ej. Planes de Uso de Terreno, Planes de Manejo) que no impliquen aprobacion de proyectos individuales",
        "name_en": "Adoption or approval of programs, plans, and regulations that do not involve individual project approval",
    },
    {
        "code": "CE-A7",
        "category": "A",
        "name_es": "Acciones de remediacion para proteccion ambiental, conservacion de recursos o planes de mitigacion requeridos por DRNA, EPA o USACE",
        "name_en": "Remediation actions for environmental protection, resource conservation, or mitigation plans required by DRNA, EPA, or USACE",
    },
    {
        "code": "CE-A8",
        "category": "A",
        "name_es": "Acciones demostradas como esencialmente similares o equivalentes a las establecidas en esta Orden",
        "name_en": "Actions demonstrated to be essentially similar or equivalent to those established in this Order",
    },
    # B. Use Authorizations in Existing Structures (No Construction)
    {
        "code": "CE-B9",
        "category": "B",
        "name_es": "Usos ministeriales en estructuras o solares existentes",
        "name_en": "Ministerial uses in existing structures or plots",
    },
    {
        "code": "CE-B10",
        "category": "B",
        "name_es": "Usos autorizados mediante procesos discrecionales (sujeto a restricciones de tamano y manufactura)",
        "name_en": "Uses authorized through discretionary processes (subject to size and manufacturing restrictions)",
    },
    {
        "code": "CE-B11",
        "category": "B",
        "name_es": "Concesiones para el uso de bienes de dominio publico",
        "name_en": "Concessions for the use of public domain assets",
    },
    # C. Construction or Demolition Actions
    {
        "code": "CE-C12",
        "category": "C",
        "name_es": "Construccion, reconstruccion o ampliacion de estructuras o infraestructura (sujeto a restricciones de ubicacion respecto a cauces de inundacion, zonas costeras y areas protegidas)",
        "name_en": "Construction, reconstruction, or expansion of structures or infrastructure (subject to location restrictions regarding floodways, coastal zones, and protected areas)",
    },
    {
        "code": "CE-C13",
        "category": "C",
        "name_es": "Remodelacion o reparaciones de estructuras existentes",
        "name_en": "Remodeling or repairs of existing structures",
    },
    {
        "code": "CE-C14",
        "category": "C",
        "name_es": "Reparacion de emergencia de obras de infraestructura",
        "name_en": "Emergency repair of infrastructure works",
    },
    {
        "code": "CE-C15",
        "category": "C",
        "name_es": "Demolicion de estructuras e infraestructura (prohibido el uso de explosivos)",
        "name_en": "Demolition of structures and infrastructure (prohibiting the use of explosives)",
    },
    # D. Installation, Replacement, Repair, or Improvement
    {
        "code": "CE-D16",
        "category": "D",
        "name_es": "Instalacion, reemplazo, reparacion o mejora de equipos y maquinaria (tuberias, generadores electricos, plantas portatiles, motores de bombas, tanques, etc.)",
        "name_en": "Installation, replacement, repair, or improvement of equipment and machinery (pipes, electricity generators, portable plants, pump motors, tanks, etc.)",
    },
    {
        "code": "CE-D17",
        "category": "D",
        "name_es": "Instalacion, reemplazo, reparacion o mejora de redes de servicio publico (lineas/torres electricas, sistemas pluviales, sistemas de bombeo para control de inundaciones)",
        "name_en": "Installation, replacement, repair, or improvement of public service networks (electric lines/towers, storm systems, pumping systems for flood control)",
    },
    {
        "code": "CE-D18",
        "category": "D",
        "name_es": "Antenas y equipos de telecomunicaciones en torres o estructuras existentes",
        "name_en": "Telecommunications antennas and equipment on existing towers or structures",
    },
    {
        "code": "CE-D19",
        "category": "D",
        "name_es": "Mobiliario urbano y senalizacion (semaforos, rotulos, vallas publicitarias)",
        "name_en": "Urban furniture and signaling (traffic lights, signs, billboards)",
    },
    {
        "code": "CE-D20",
        "category": "D",
        "name_es": "Obras de infraestructura dentro del mismo perimetro existente (puentes, muelles, rieles)",
        "name_en": "Infrastructure works within the same footprint (bridges, docks, rails)",
    },
    {
        "code": "CE-D21",
        "category": "D",
        "name_es": "Sistemas de monitoreo para medicion ambiental u operacional",
        "name_en": "Monitoring systems for environmental or operational measurement",
    },
    {
        "code": "CE-D22",
        "category": "D",
        "name_es": "Recubrimientos protectores para equipos, terrenos o recursos naturales",
        "name_en": "Protective coatings for equipment, land, or natural resources",
    },
    # E. Atmospheric Emission Sources
    {
        "code": "CE-E23",
        "category": "E",
        "name_es": "Modificacion o ajuste operacional de equipos, procesos o combustibles en una instalacion existente previamente autorizada a emitir contaminantes atmosfericos (siempre que se mantenga dentro de su categoria de potencial de emision)",
        "name_en": "Modification or operational adjustment of equipment, processes, or fuels in an existing facility previously authorized to emit atmospheric pollutants (provided it stays within its emission potential category)",
    },
    # F. Maintenance, Monitoring, and Landscaping
    {
        "code": "CE-F24",
        "category": "F",
        "name_es": "Mantenimiento sin construccion de infraestructura, incluyendo pavimentacion o escarificacion de carreteras, aceras y puentes",
        "name_en": "Maintenance without infrastructure construction, including paving or scarification of roads, sidewalks, and bridges",
    },
    {
        "code": "CE-F25",
        "category": "F",
        "name_es": "Limpieza y conservacion de cuerpos de agua (debe mantener la geometria original)",
        "name_en": "Cleaning and conservation of water bodies (must maintain original geometry)",
    },
    {
        "code": "CE-F26",
        "category": "F",
        "name_es": "Dragado de mantenimiento para infraestructura",
        "name_en": "Maintenance dredging for infrastructure",
    },
    {
        "code": "CE-F27",
        "category": "F",
        "name_es": "Desmonte de terrenos para actividades agricolas (no se permite construccion)",
        "name_en": "Land clearing for agricultural activities (no construction allowed)",
    },
    {
        "code": "CE-F28",
        "category": "F",
        "name_es": "Desmonte de terrenos que requiere permiso simple de extraccion de materiales de corteza",
        "name_en": "Land clearing requiring a simple extraction permit for crust materials",
    },
    # G. Segregation Actions
    {
        "code": "CE-G29",
        "category": "G",
        "name_es": "Segregaciones ministeriales",
        "name_en": "Ministerial segregations",
    },
    {
        "code": "CE-G30",
        "category": "G",
        "name_es": "Segregaciones de hasta diez (10) lotes con areas menores a las requeridas",
        "name_en": "Segregations of up to ten (10) lots with smaller areas than required",
    },
    {
        "code": "CE-G31",
        "category": "G",
        "name_es": "Segregaciones donde el area del lote propuesto es igual o mayor al 20% del minimo requerido por el distrito",
        "name_en": "Segregations where the proposed lot area is equal to or greater than 20% of the minimum required by the district",
    },
]

# Category descriptions for OA 2025-10
CATEGORICAL_EXCLUSION_CATEGORIES = {
    "A": "Acciones Generales",
    "B": "Autorizaciones de Uso en Estructuras Existentes (Sin Construccion)",
    "C": "Acciones de Construccion o Demolicion",
    "D": "Instalacion, Reemplazo, Reparacion o Mejora",
    "E": "Fuentes de Emision Atmosferica",
    "F": "Mantenimiento, Monitoreo y Paisajismo",
    "G": "Acciones de Segregacion",
}


class PCOCService:
    """Service for PCOC validation business logic"""

    @staticmethod
    def get_exempt_categories() -> Dict[str, List[Dict]]:
        """Get all exempt work categories"""
        return {
            "obras_exentas": EXEMPT_WORK_CATEGORIES,
            "obras_menores": MINOR_WORK_EXEMPTIONS,
        }

    @staticmethod
    def get_categorical_exclusions() -> Dict[str, Any]:
        """Get categorical exclusions from OA 2025-10"""
        return {
            "exclusions": CATEGORICAL_EXCLUSIONS_OA_2025_10,
            "categories": CATEGORICAL_EXCLUSION_CATEGORIES,
        }

    @staticmethod
    def get_district_parameters(zoning_code: str) -> Optional[Dict[str, Any]]:
        """
        Get the parameters for a specific zoning district.
        These are used in Filter 3 to compare project values against requirements.
        """
        rules_db = get_rules_db()
        district = rules_db.get_zoning_district(zoning_code)

        if not district:
            return None

        # Build parameters object with available data
        params = {
            "code": district.get("code"),
            "name_es": district.get("name_es"),
            "name_en": district.get("name_en"),
            "category": district.get("category"),
            "parameters": {
                "max_height": district.get("max_height"),
                "max_coverage": district.get("max_coverage"),
                "min_lot_size": district.get("min_lot_size"),
                # Additional parameters can be added as needed
            },
        }

        return params

    @staticmethod
    def analyze_filter1(filter1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Filter 1 data to determine if work is exempt.

        Args:
            filter1_data: Contains proposed_use and exempt_selections

        Returns:
            Analysis result with is_exempt and exempt_reason
        """
        proposed_use = filter1_data.get("proposed_use", "").lower()
        exempt_selections = filter1_data.get("exempt_selections", [])

        # If user selected exempt categories, check if they apply
        if exempt_selections:
            all_exempt = EXEMPT_WORK_CATEGORIES + MINOR_WORK_EXEMPTIONS
            selected_exemptions = [e for e in all_exempt if e["code"] in exempt_selections]

            if selected_exemptions:
                exemption_names = [e["name_es"] for e in selected_exemptions]
                return {
                    "is_exempt": True,
                    "exempt_reason": f"La obra se clasifica como exenta bajo las categorias: {', '.join(exemption_names)}",
                    "exempt_categories": selected_exemptions,
                    "action_required": "Debe radicar una Solicitud de Obra Exenta para validacion y pago de arbitrios.",
                }

        # Check proposed use against exempt categories using keyword matching
        exempt_keywords = {
            "pintura": "EXC-01",
            "pintar": "EXC-01",
            "sellado": "EXC-02",
            "sellar techo": "EXC-02",
            "jardineria": "EXC-03",
            "grietas": "EXC-04",
            "goteras": "EXC-04",
            "empanete": "EXC-05",
            "enlucido": "EXC-05",
            "losetas": "EXC-06",
            "azulejos": "EXC-06",
            "ceramica": "EXC-06",
            "acusticos": "EXC-07",
            "luminarias": "EXC-07",
            "puertas": "EXC-08",
            "ventanas": "EXC-08",
            "gypsum": "EXC-11",
            "sheetrock": "EXC-11",
            "verja": "EXC-12",
            "reja": "EXC-12",
            "asfaltar": "EXC-13",
        }

        matched_codes = []
        for keyword, code in exempt_keywords.items():
            if keyword in proposed_use:
                matched_codes.append(code)

        if matched_codes:
            all_exempt = EXEMPT_WORK_CATEGORIES + MINOR_WORK_EXEMPTIONS
            matched_exemptions = [e for e in all_exempt if e["code"] in matched_codes]

            return {
                "is_exempt": True,
                "exempt_reason": "El uso propuesto parece corresponder a una obra exenta.",
                "ai_interpretation": f"Se detectaron las siguientes categorias exentas basado en la descripcion: {', '.join([e['name_es'] for e in matched_exemptions])}",
                "exempt_categories": matched_exemptions,
                "action_required": "Debe radicar una Solicitud de Obra Exenta para validacion y pago de arbitrios.",
                "needs_confirmation": True,
            }

        # Not exempt - requires construction permit
        return {
            "is_exempt": False,
            "exempt_reason": None,
            "ai_interpretation": "El uso propuesto no parece corresponder a una obra exenta. Requiere Permiso de Construccion.",
            "action_required": "Proceda al Filtro 2 para evaluar zonas sobrepuestas.",
        }

    @staticmethod
    def analyze_filter2(filter2_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Filter 2 data to determine required recommendations.

        Args:
            filter2_data: Contains zona_historica, zona_turistica, zona_inundacion flags

        Returns:
            Analysis result with required_recommendations
        """
        required_recommendations = []
        action_items = []

        # Check zona historica
        zona_historica = filter2_data.get("zona_historica", False)
        if zona_historica:
            required_recommendations.append({
                "agency": "ICP",
                "name": "Instituto de Cultura Puertorriquena",
                "requirement": "Recomendacion de Arqueologia y Conservacion Historica (SRA)",
                "deadline_days": 30,
                "section": "Sec. 10.2.2.3 RC",
            })
            action_items.append("Obtener recomendacion del ICP previo a la autorizacion")

        # Check zona turistica
        zona_turistica = filter2_data.get("zona_turistica", False)
        if zona_turistica:
            required_recommendations.append({
                "agency": "CT",
                "name": "Compania de Turismo",
                "requirement": "Recomendacion previa por escrito",
                "deadline_days": 30,
                "section": "RC Seccion correspondiente",
            })
            action_items.append("Obtener recomendacion de la Compania de Turismo")

        # Check zona inundacion
        zona_inundacion = filter2_data.get("zona_inundacion", False)
        if zona_inundacion:
            required_recommendations.append({
                "agency": "JP",
                "name": "Junta de Planificacion",
                "requirement": "Certificacion de Inundabilidad",
                "deadline_days": 30,
                "section": "Sec. 3.2.1.2 RC, Reglamento 13",
            })
            action_items.append("Presentar Certificacion de Inundabilidad de la JP")
            action_items.append("Cumplir con disposiciones del Reglamento de Planificacion Num. 13")

        has_overlays = len(required_recommendations) > 0

        return {
            "has_overlays": has_overlays,
            "required_recommendations": required_recommendations,
            "action_items": action_items,
            "can_proceed": True,  # Can proceed but must obtain recommendations
            "message": "Debe obtener las recomendaciones requeridas antes de solicitar el permiso." if has_overlays else "No se requieren recomendaciones adicionales por ubicacion.",
        }

    @staticmethod
    def analyze_filter3(filter3_data: Dict[str, Any], zoning_code: str) -> Dict[str, Any]:
        """
        Analyze Filter 3 data to determine if ministerial or discretionary.

        Args:
            filter3_data: Contains project_params with user-entered values
            zoning_code: The zoning district code

        Returns:
            Analysis result with is_ministerial and comparison results
        """
        project_params = filter3_data.get("project_params", {})

        # Get district requirements
        district_params = PCOCService.get_district_parameters(zoning_code)
        if not district_params:
            return {
                "is_ministerial": None,
                "error": f"No se encontraron parametros para el distrito {zoning_code}",
            }

        requirements = district_params.get("parameters", {})
        comparison_results = []
        non_compliant_params = []

        # Compare each parameter
        def parse_numeric(value: str) -> Optional[float]:
            """Extract numeric value from string like '40%' or '2 pisos' or '800 m2'"""
            if not value:
                return None
            import re
            match = re.search(r"[\d.]+", str(value))
            return float(match.group()) if match else None

        # Height comparison
        if "altura" in project_params and requirements.get("max_height"):
            project_altura = parse_numeric(project_params.get("altura"))
            max_altura = parse_numeric(requirements.get("max_height"))
            if project_altura and max_altura:
                compliant = project_altura <= max_altura
                comparison_results.append({
                    "param": "altura",
                    "project_value": project_params.get("altura"),
                    "requirement": requirements.get("max_height"),
                    "compliant": compliant,
                })
                if not compliant:
                    non_compliant_params.append("altura")

        # Coverage comparison
        if "area_ocupacion" in project_params and requirements.get("max_coverage"):
            project_coverage = parse_numeric(project_params.get("area_ocupacion"))
            max_coverage = parse_numeric(requirements.get("max_coverage"))
            if project_coverage and max_coverage:
                compliant = project_coverage <= max_coverage
                comparison_results.append({
                    "param": "area_ocupacion",
                    "project_value": project_params.get("area_ocupacion"),
                    "requirement": requirements.get("max_coverage"),
                    "compliant": compliant,
                })
                if not compliant:
                    non_compliant_params.append("area_ocupacion")

        # Lot size comparison
        if "tamano_solar" in project_params and requirements.get("min_lot_size"):
            project_lot = parse_numeric(project_params.get("tamano_solar"))
            min_lot = parse_numeric(requirements.get("min_lot_size"))
            if project_lot and min_lot:
                compliant = project_lot >= min_lot
                comparison_results.append({
                    "param": "tamano_solar",
                    "project_value": project_params.get("tamano_solar"),
                    "requirement": requirements.get("min_lot_size"),
                    "compliant": compliant,
                })
                if not compliant:
                    non_compliant_params.append("tamano_solar")

        # Determine if ministerial
        is_ministerial = len(non_compliant_params) == 0

        return {
            "is_ministerial": is_ministerial,
            "district_requirements": requirements,
            "comparison_results": comparison_results,
            "non_compliant_params": non_compliant_params,
            "message": "El proyecto cumple con todos los parametros del distrito. Puede ser evaluado como asunto Ministerial." if is_ministerial else f"El proyecto no cumple con los siguientes parametros: {', '.join(non_compliant_params)}. Requiere evaluacion Discrecional por la Junta Adjudicativa.",
        }

    @staticmethod
    def analyze_filter4(proposed_use: str) -> Dict[str, Any]:
        """
        Analyze Filter 4 data for environmental compliance.
        Checks if the proposed use falls under categorical exclusions (OA 2025-10).

        Args:
            proposed_use: The proposed use description

        Returns:
            Analysis result with categorical exclusion determination
        """
        proposed_lower = proposed_use.lower() if proposed_use else ""

        # Keyword mapping to categorical exclusion codes
        exclusion_mappings = [
            # Category B - Uses in existing structures
            (["uso ministerial", "estructura existente", "solar existente"], "CE-B9"),
            (["uso discrecional", "proceso discrecional"], "CE-B10"),
            # Category C - Construction/Demolition
            (["construccion", "reconstruccion", "ampliacion"], "CE-C12"),
            (["remodelacion", "reparacion", "reparaciones"], "CE-C13"),
            (["emergencia", "reparacion de emergencia"], "CE-C14"),
            (["demolicion", "demoler"], "CE-C15"),
            # Category D - Installation/Replacement
            (["instalacion de equipo", "reemplazo", "maquinaria", "generador", "tanque", "bomba"], "CE-D16"),
            (["linea electrica", "sistema pluvial", "torre electrica"], "CE-D17"),
            (["antena", "telecomunicacion", "torre de comunicacion"], "CE-D18"),
            (["semaforo", "rotulo", "valla", "senalizacion"], "CE-D19"),
            (["puente", "muelle", "riel", "infraestructura existente"], "CE-D20"),
            (["monitoreo", "sistema de medicion"], "CE-D21"),
            (["recubrimiento", "protector", "coating"], "CE-D22"),
            # Category F - Maintenance
            (["mantenimiento", "pavimentacion", "acera"], "CE-F24"),
            (["limpieza", "cuerpo de agua", "conservacion"], "CE-F25"),
            (["dragado", "mantenimiento de infraestructura"], "CE-F26"),
            (["desmonte", "agricola", "agricultura", "finca"], "CE-F27"),
            # Category G - Segregation
            (["segregacion", "subdivision", "lotes"], "CE-G29"),
        ]

        matched_exclusion = None
        matched_code = None

        for keywords, code in exclusion_mappings:
            if any(kw in proposed_lower for kw in keywords):
                matched_code = code
                # Find the full exclusion details
                for exc in CATEGORICAL_EXCLUSIONS_OA_2025_10:
                    if exc["code"] == code:
                        matched_exclusion = exc
                        break
                break

        if matched_exclusion:
            category_name = CATEGORICAL_EXCLUSION_CATEGORIES.get(matched_exclusion["category"], "")
            return {
                "is_categorical_exclusion": True,
                "exclusion_code": matched_exclusion["code"],
                "exclusion_category": f"{matched_exclusion['category']}. {category_name}",
                "exclusion_name": matched_exclusion["name_es"],
                "exclusion_reason": f"El uso propuesto cualifica como Exclusion Categorica bajo OA 2025-10 de DRNA: {matched_exclusion['name_es']}",
                "requires_ea_dia": False,
                "message": "La Exclusion Categorica (EXC) se emite de forma automatica a traves del PA o la OGPe. Debe cumplir con las condiciones generales y restricciones especificas definidas en la orden.",
            }
        else:
            return {
                "is_categorical_exclusion": False,
                "exclusion_code": None,
                "exclusion_category": None,
                "exclusion_name": None,
                "exclusion_reason": None,
                "requires_ea_dia": True,
                "message": "El proyecto no parece cualificar para ninguna Exclusion Categorica bajo OA 2025-10. Requiere presentar una Evaluacion Ambiental (EA) o Declaracion de Impacto Ambiental (DIA) ante la DECA.",
            }

    @staticmethod
    def generate_final_result(validation) -> Dict[str, Any]:
        """
        Generate the final PCOC validation result.

        Args:
            validation: The PCOCValidation model instance

        Returns:
            Final result dictionary with summary, action items, and recommendations
        """
        filter1 = validation.filter1_data or {}
        filter2 = validation.filter2_data or {}
        filter3 = validation.filter3_data or {}
        filter4 = validation.filter4_data or {}

        action_items = []
        recommendations = []

        # Determine permit type
        is_exempt = filter1.get("is_exempt", False)
        is_ministerial = filter3.get("is_ministerial", False)
        has_overlays = filter2.get("has_overlays", False)

        if is_exempt:
            permit_type = "obra_exenta"
            summary = "La obra cualifica como Obra Exenta y no requiere Permiso de Construccion formal."
            action_items.append({
                "action": "Radicar Solicitud de Obra Exenta",
                "description": "Para validacion y pago de arbitrios municipales",
                "required": True,
            })
        elif is_ministerial:
            permit_type = "ministerial"
            summary = "El proyecto puede ser evaluado como asunto Ministerial."
            action_items.append({
                "action": "Solicitar Permiso de Construccion",
                "description": "Puede ser evaluado por OGPe, Municipio (I a III) o Profesional Autorizado (PA)",
                "required": True,
            })
        else:
            permit_type = "discrecional"
            summary = "El proyecto requiere evaluacion Discrecional por la Junta Adjudicativa."
            action_items.append({
                "action": "Solicitar Permiso de Construccion (Discrecional)",
                "description": "Debe ser evaluado por la Junta Adjudicativa de la OGPe o del Municipio. Puede requerir Vista Publica.",
                "required": True,
            })

            non_compliant = filter3.get("non_compliant_params", [])
            if non_compliant:
                action_items.append({
                    "action": "Solicitar variacion o excepcion",
                    "description": f"Parametros no conformes: {', '.join(non_compliant)}",
                    "required": True,
                })

        # Add overlay-related action items
        if has_overlays:
            overlay_recommendations = filter2.get("required_recommendations", [])
            for rec in overlay_recommendations:
                action_items.append({
                    "action": f"Obtener recomendacion de {rec['agency']}",
                    "description": rec["requirement"],
                    "deadline": f"{rec['deadline_days']} dias",
                    "required": True,
                })

        # Add environmental compliance
        if filter4.get("requires_ea_dia", False):
            action_items.append({
                "action": "Presentar EA o DIA",
                "description": "Evaluacion Ambiental o Declaracion de Impacto Ambiental ante DECA",
                "required": True,
            })
            recommendations.append("El proyecto no cualifica para Exclusion Categorica. Debe consultar con un especialista ambiental.")
        else:
            recommendations.append("El proyecto cualifica para Exclusion Categorica (EXC) que se emite automaticamente.")

        # Historical zone warning
        if filter2.get("zona_historica", False):
            recommendations.append("IMPORTANTE: Cualquier obra exenta en Zona Historica requiere autorizacion del ICP mediante SRA.")

        viable = not filter4.get("requires_ea_dia", False) or is_exempt

        return {
            "permit_type": permit_type,
            "summary": summary,
            "action_items": action_items,
            "recommendations": recommendations,
            "viable": viable,
            "filter_summary": {
                "filter1_exempt": is_exempt,
                "filter2_has_overlays": has_overlays,
                "filter3_ministerial": is_ministerial,
                "filter4_categorical_exclusion": filter4.get("is_categorical_exclusion", False),
            },
        }
