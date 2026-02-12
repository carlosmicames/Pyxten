"""
Document Validation Service
Handles document requirements, validation, and Memorial Explicativo generation
for PCOC and Permiso Unico applications
"""
from typing import Dict, List, Any, Optional


class DocumentService:
    """Service for document validation operations"""

    # =========================================================================
    # PCOC Document Requirements
    # Based on Reglamento Conjunto requirements for construction permits
    # =========================================================================
    PCOC_DOCUMENTS = [
        {
            "code": "planos_arquitectura",
            "name": "Planos de Arquitectura",
            "description": "Planos arquitectonicos certificados por un arquitecto licenciado",
            "required": True,
            "conditional": None,
        },
        {
            "code": "planos_estructurales",
            "name": "Planos Estructurales",
            "description": "Planos estructurales certificados por un ingeniero estructural licenciado",
            "required": True,
            "conditional": None,
        },
        {
            "code": "planos_electricos",
            "name": "Planos Electricos",
            "description": "Planos electricos certificados por un ingeniero electrico o perito electricista",
            "required": True,
            "conditional": None,
        },
        {
            "code": "planos_sanitarios",
            "name": "Planos Sanitarios",
            "description": "Planos de sistema sanitario y pluvial",
            "required": True,
            "conditional": None,
        },
        {
            "code": "planos_mecanicos",
            "name": "Planos Mecanicos",
            "description": "Planos de sistemas mecanicos (HVAC, etc.)",
            "required": False,
            "conditional": "Si el proyecto incluye sistemas de aire acondicionado central o ventilacion mecanica",
        },
        {
            "code": "certificacion_inundabilidad",
            "name": "Certificacion de Inundabilidad (FEMA)",
            "description": "Certificacion de zona de inundacion emitida por FEMA o profesional autorizado",
            "required": True,
            "conditional": None,
        },
        {
            "code": "certificacion_servidumbre",
            "name": "Certificacion de Localizacion de Servidumbre",
            "description": "Certificacion de que no hay servidumbres que afecten el proyecto",
            "required": True,
            "conditional": None,
        },
        {
            "code": "delimitacion_zmt",
            "name": "Delimitacion de Zonas Maritimo-Terrestres",
            "description": "Delimitacion de ZMT emitida por DRNA si el predio colinda con costa",
            "required": False,
            "conditional": "Si el predio colinda con la zona maritimo-terrestre",
        },
        {
            "code": "consulta_ubicacion",
            "name": "Consulta de Ubicacion (JP/OGPe)",
            "description": "Consulta de ubicacion de la Junta de Planificacion u OGPe",
            "required": True,
            "conditional": None,
        },
        {
            "code": "marbete_crim",
            "name": "Marbete CRIM",
            "description": "Comprobante de pago de contribuciones (CRIM)",
            "required": True,
            "conditional": None,
        },
        {
            "code": "fotos_predio",
            "name": "Fotos del Predio",
            "description": "Fotografias actuales del predio mostrando condiciones existentes",
            "required": True,
            "conditional": None,
        },
        {
            "code": "evaluacion_ambiental",
            "name": "Evaluacion Ambiental",
            "description": "Documento de evaluacion ambiental (EA) o declaracion de impacto ambiental (DIA)",
            "required": False,
            "conditional": "Si el proyecto no cualifica para exclusion categorica",
        },
        {
            "code": "estudio_transito",
            "name": "Estudio de Transito",
            "description": "Estudio de impacto de transito",
            "required": False,
            "conditional": "Si el proyecto genera mas de 100 viajes diarios o 10 viajes en hora pico",
        },
        {
            "code": "estudio_ruido",
            "name": "Estudio de Ruido",
            "description": "Estudio de impacto de ruido",
            "required": False,
            "conditional": "Si el proyecto puede generar niveles de ruido significativos",
        },
        {
            "code": "certificacion_aee",
            "name": "Certificacion de AEE",
            "description": "Certificacion de disponibilidad de servicio electrico (AEE/LUMA)",
            "required": True,
            "conditional": None,
        },
        {
            "code": "certificacion_aaa",
            "name": "Certificacion de AAA",
            "description": "Certificacion de disponibilidad de servicio de agua y alcantarillado (AAA)",
            "required": True,
            "conditional": None,
        },
        {
            "code": "memorial_explicativo",
            "name": "Memorial Explicativo",
            "description": "Documento narrativo que describe el proyecto (puede ser auto-generado)",
            "required": True,
            "conditional": None,
        },
    ]

    # =========================================================================
    # Permiso Unico Document Requirements
    # =========================================================================
    PERMISO_UNICO_DOCUMENTS = [
        {
            "code": "legitimacion_activa",
            "name": "Legitimacion Activa",
            "description": "Documento que acredita el derecho del solicitante sobre la propiedad",
            "required": True,
            "conditional": None,
        },
        {
            "code": "identificacion",
            "name": "Identificacion del Solicitante",
            "description": "Copia de identificacion con foto (licencia o pasaporte)",
            "required": True,
            "conditional": None,
        },
        {
            "code": "estatus_corporativo",
            "name": "Estatus Corporativo",
            "description": "Certificado de existencia corporativa del Departamento de Estado",
            "required": False,
            "conditional": "Si el solicitante es una corporacion o entidad juridica",
        },
        {
            "code": "poder_representacion",
            "name": "Poder de Representacion",
            "description": "Poder notarial si el solicitante actua en representacion de otro",
            "required": False,
            "conditional": "Si el solicitante actua como representante",
        },
        {
            "code": "escritura_propiedad",
            "name": "Escritura de Propiedad",
            "description": "Copia de la escritura de propiedad o contrato de arrendamiento",
            "required": True,
            "conditional": None,
        },
        {
            "code": "plano_mensura",
            "name": "Plano de Mensura",
            "description": "Plano de mensura certificado por agrimensor licenciado",
            "required": True,
            "conditional": None,
        },
        {
            "code": "certificacion_deuda_crim",
            "name": "Certificacion de Deuda CRIM",
            "description": "Certificacion negativa de deuda del CRIM",
            "required": True,
            "conditional": None,
        },
        {
            "code": "certificacion_hacienda",
            "name": "Certificacion de Hacienda",
            "description": "Certificacion de radicacion de planillas del Departamento de Hacienda",
            "required": True,
            "conditional": None,
        },
        {
            "code": "certificacion_asume",
            "name": "Certificacion de ASUME",
            "description": "Certificacion de cumplimiento de pension alimentaria",
            "required": True,
            "conditional": None,
        },
    ]

    @classmethod
    def get_pcoc_requirements(cls) -> List[Dict[str, Any]]:
        """Get all PCOC document requirements"""
        return cls.PCOC_DOCUMENTS

    @classmethod
    def get_permiso_unico_requirements(cls) -> List[Dict[str, Any]]:
        """Get all Permiso Unico document requirements"""
        return cls.PERMISO_UNICO_DOCUMENTS

    @classmethod
    def get_requirements_by_type(cls, validation_type: str) -> List[Dict[str, Any]]:
        """Get document requirements by validation type"""
        if validation_type == "pcoc":
            return cls.PCOC_DOCUMENTS
        elif validation_type == "permiso_unico":
            return cls.PERMISO_UNICO_DOCUMENTS
        return []

    @classmethod
    def initialize_documents_checklist(cls, validation_type: str) -> Dict[str, Any]:
        """Initialize an empty documents checklist for a validation type"""
        requirements = cls.get_requirements_by_type(validation_type)
        documents = {}
        for req in requirements:
            documents[req["code"]] = {
                "required": req["required"],
                "optional": not req["required"],
                "conditional": req.get("conditional"),
                "uploaded": False,
                "file_url": None,
                "file_name": None,
                "verified": False,
                "notes": "",
            }
        return documents

    @classmethod
    def validate_documents_completeness(cls, documents: Dict[str, Any], validation_type: str) -> Dict[str, Any]:
        """
        Check if all required documents are uploaded and verified
        Returns a summary of document validation status
        """
        requirements = cls.get_requirements_by_type(validation_type)

        total_required = 0
        total_optional = 0
        uploaded_required = 0
        uploaded_optional = 0
        verified_required = 0
        verified_optional = 0
        missing_required = []
        missing_optional = []

        for req in requirements:
            code = req["code"]
            doc_status = documents.get(code, {})

            if req["required"]:
                total_required += 1
                if doc_status.get("uploaded"):
                    uploaded_required += 1
                    if doc_status.get("verified"):
                        verified_required += 1
                else:
                    missing_required.append({
                        "code": code,
                        "name": req["name"],
                        "description": req["description"],
                    })
            else:
                total_optional += 1
                if doc_status.get("uploaded"):
                    uploaded_optional += 1
                    if doc_status.get("verified"):
                        verified_optional += 1
                else:
                    missing_optional.append({
                        "code": code,
                        "name": req["name"],
                        "description": req["description"],
                        "conditional": req.get("conditional"),
                    })

        is_complete = len(missing_required) == 0

        return {
            "is_complete": is_complete,
            "total_required": total_required,
            "total_optional": total_optional,
            "uploaded_required": uploaded_required,
            "uploaded_optional": uploaded_optional,
            "verified_required": verified_required,
            "verified_optional": verified_optional,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "progress_percent": round((uploaded_required / total_required * 100) if total_required > 0 else 0, 1),
        }

    @classmethod
    def generate_memorial_explicativo(
        cls,
        project_name: str,
        property_address: str,
        municipality: str,
        pcoc_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Memorial Explicativo content based on project data and PCOC validation results
        """
        # Extract data from PCOC validation if available
        zoning_code = ""
        proposed_use = ""
        permit_type = ""
        is_ministerial = None
        is_categorical_exclusion = None
        exclusion_category = ""
        required_recommendations = []

        if pcoc_data:
            zoning_code = pcoc_data.get("zoning_code", "")

            filter1 = pcoc_data.get("filter1_data", {}) or {}
            proposed_use = filter1.get("proposed_use", "")

            filter2 = pcoc_data.get("filter2_data", {}) or {}
            required_recommendations = filter2.get("required_recommendations", []) or []

            filter3 = pcoc_data.get("filter3_data", {}) or {}
            is_ministerial = filter3.get("is_ministerial")

            filter4 = pcoc_data.get("filter4_data", {}) or {}
            is_categorical_exclusion = filter4.get("is_categorical_exclusion")
            exclusion_category = filter4.get("exclusion_category", "")

            result = pcoc_data.get("result", {}) or {}
            permit_type = result.get("permit_type", "")

        # Build Memorial Explicativo sections
        project_description = f"""
El presente proyecto, denominado "{project_name}", consiste en {proposed_use if proposed_use else "[descripcion del uso propuesto]"}.
El proyecto se desarrollara en la propiedad ubicada en {property_address}, {municipality}, Puerto Rico.
""".strip()

        location_description = f"""
La propiedad se encuentra ubicada en el municipio de {municipality}.
Direccion fisica: {property_address}
Codigo de zonificacion: {zoning_code if zoning_code else "[codigo de zonificacion]"}
""".strip()

        zoning_info = f"""
Segun el Plan de Ordenamiento Territorial (POT) y el Reglamento Conjunto de Permisos,
la propiedad esta clasificada bajo el distrito de zonificacion {zoning_code if zoning_code else "[codigo]"}.
El uso propuesto es compatible con los usos permitidos en este distrito.
""".strip()

        construction_details = f"""
[Incluir detalles especificos de la construccion propuesta:]
- Area de construccion: [metros cuadrados]
- Numero de niveles: [cantidad]
- Uso propuesto: {proposed_use if proposed_use else "[uso]"}
- Altura propuesta: [metros]
- Estacionamientos provistos: [cantidad]
""".strip()

        # Environmental compliance section
        if is_categorical_exclusion:
            environmental_compliance = f"""
El proyecto cualifica para Exclusion Categorica segun la Orden Administrativa OA 2025-10 del DRNA.
Categoria de exclusion aplicable: {exclusion_category if exclusion_category else "[categoria]"}
Por lo tanto, no se requiere Evaluacion Ambiental (EA) ni Declaracion de Impacto Ambiental (DIA).
""".strip()
        elif is_categorical_exclusion is False:
            environmental_compliance = """
El proyecto NO cualifica para Exclusion Categorica.
Se requiere la preparacion de un Documento Ambiental (Evaluacion Ambiental o DIA) para cumplir
con los requisitos ambientales aplicables.
""".strip()
        else:
            environmental_compliance = """
[Pendiente determinar si el proyecto cualifica para exclusion categorica]
""".strip()

        # Permit type justification
        if permit_type == "obra_exenta":
            permit_type_justification = """
Basado en el analisis realizado, la obra propuesta cualifica como OBRA EXENTA
segun la Seccion 3.2.4 del Reglamento Conjunto. Por lo tanto, no se requiere
permiso de construccion para este proyecto.
""".strip()
        elif permit_type == "ministerial" or is_ministerial:
            permit_type_justification = """
Basado en el analisis realizado, el proyecto cualifica para tramite MINISTERIAL.
Todos los parametros de construccion propuestos cumplen con los requisitos del
distrito de zonificacion aplicable, por lo que el permiso puede ser otorgado
sin necesidad de vista publica o proceso discrecional.
""".strip()
        elif permit_type == "discrecional" or is_ministerial is False:
            permit_type_justification = """
Basado en el analisis realizado, el proyecto requiere tramite DISCRECIONAL.
Uno o mas parametros de construccion propuestos exceden los limites ministeriales
del distrito de zonificacion, por lo que se requiere evaluacion adicional
y posible vista publica.
""".strip()
        else:
            permit_type_justification = """
[Pendiente determinar tipo de tramite]
""".strip()

        # Add recommendations section if there are any
        additional_notes = ""
        if required_recommendations:
            recommendations_text = "\n".join([f"- {rec}" for rec in required_recommendations])
            additional_notes = f"""
Recomendaciones adicionales identificadas:
{recommendations_text}

Estas recomendaciones deben ser atendidas como parte del proceso de permisos.
""".strip()

        return {
            "generated": True,
            "project_description": project_description,
            "location_description": location_description,
            "zoning_info": zoning_info,
            "construction_details": construction_details,
            "environmental_compliance": environmental_compliance,
            "permit_type_justification": permit_type_justification,
            "additional_notes": additional_notes,
            "pdf_url": None,
        }
