"""
Regulatory data loader - loads JSON data files
Ported from src/database/rules_loader.py
"""
from typing import Dict, List, Optional
from functools import lru_cache


# Embedded data from data/regulations/use_classifications.json
USE_TYPES = [
    {
        "code": "RES-SF",
        "name_es": "Residencial Unifamiliar",
        "name_en": "Single Family Residential",
        "category": "residential",
        "compatible_zones": ["R-B", "R-I", "R-U", "R-C", "RT-I", "RT-A"],
        "ministerial": True,
        "description_es": "Vivienda para una sola familia",
    },
    {
        "code": "RES-MF",
        "name_es": "Residencial Multifamiliar",
        "name_en": "Multifamily Residential",
        "category": "residential",
        "compatible_zones": ["R-I", "R-U", "R-C", "RT-I", "RT-A"],
        "ministerial": True,
        "description_es": "Edificio con multiples unidades residenciales",
    },
    {
        "code": "COM-OFFICE",
        "name_es": "Oficina Profesional",
        "name_en": "Professional Office",
        "category": "commercial",
        "compatible_zones": ["C-L", "C-I", "C-C", "R-C", "C-T"],
        "ministerial": True,
        "parking_required": "1 per 30 m2",
        "description_es": "Oficina administrativa o profesional",
    },
    {
        "code": "COM-RETAIL",
        "name_es": "Comercio al Detal",
        "name_en": "Retail",
        "category": "commercial",
        "compatible_zones": ["C-L", "C-I", "C-C", "R-C", "C-T"],
        "ministerial": True,
        "parking_required": "1 per 25 m2",
        "description_es": "Venta al publico de mercancias",
    },
    {
        "code": "COM-RESTAURANT",
        "name_es": "Restaurante",
        "name_en": "Restaurant",
        "category": "commercial",
        "compatible_zones": ["C-L", "C-I", "C-C", "R-C", "C-T"],
        "ministerial": False,
        "requires_health_permit": True,
        "parking_required": "1 per 10 seats",
        "description_es": "Establecimiento de comida y bebida",
    },
    {
        "code": "COM-WAREHOUSE",
        "name_es": "Almacen",
        "name_en": "Warehouse",
        "category": "commercial",
        "compatible_zones": ["C-I", "C-C", "I-L", "I-E"],
        "ministerial": True,
        "description_es": "Almacenamiento de mercancias",
    },
    {
        "code": "IND-LIGHT",
        "name_es": "Manufactura Liviana",
        "name_en": "Light Manufacturing",
        "category": "industrial",
        "compatible_zones": ["I-L", "I-E", "I-P"],
        "ministerial": False,
        "requires_environmental": True,
        "description_es": "Produccion industrial sin contaminantes",
    },
    {
        "code": "IND-HEAVY",
        "name_es": "Manufactura Pesada",
        "name_en": "Heavy Manufacturing",
        "category": "industrial",
        "compatible_zones": ["I-P"],
        "ministerial": False,
        "requires_environmental": True,
        "description_es": "Produccion industrial pesada",
    },
    {
        "code": "TOURIST-HOTEL",
        "name_es": "Hotel o Hospedaje Turistico",
        "name_en": "Hotel or Tourist Lodging",
        "category": "tourist",
        "compatible_zones": ["RT-I", "RT-A", "C-T", "DTS", "C-C"],
        "ministerial": False,
        "requires_environmental": True,
        "description_es": "Alojamiento turistico comercial",
    },
    {
        "code": "AGR-FARM",
        "name_es": "Finca Agricola",
        "name_en": "Agricultural Farm",
        "category": "agricultural",
        "compatible_zones": ["A-G", "A-P", "R-G"],
        "ministerial": True,
        "description_es": "Cultivo de productos agricolas",
    },
    {
        "code": "AGR-LIVESTOCK",
        "name_es": "Ganaderia",
        "name_en": "Livestock",
        "category": "agricultural",
        "compatible_zones": ["A-G", "R-G"],
        "ministerial": True,
        "description_es": "Crianza de animales",
    },
    {
        "code": "RURAL-RESIDENCE",
        "name_es": "Residencia Rural",
        "name_en": "Rural Residence",
        "category": "rural",
        "compatible_zones": ["R-G", "ARD", "A-G"],
        "ministerial": True,
        "description_es": "Vivienda en zona rural",
    },
    {
        "code": "INST-SCHOOL",
        "name_es": "Escuela o Centro Educativo",
        "name_en": "School or Educational Center",
        "category": "institutional",
        "compatible_zones": ["D-G", "R-I", "R-U"],
        "ministerial": False,
        "description_es": "Institucion educativa",
    },
    {
        "code": "INST-HEALTH",
        "name_es": "Centro de Salud",
        "name_en": "Health Center",
        "category": "institutional",
        "compatible_zones": ["D-G", "C-I", "C-C"],
        "ministerial": False,
        "description_es": "Clinica u hospital",
    },
    {
        "code": "INST-RELIGIOUS",
        "name_es": "Templo o Iglesia",
        "name_en": "Church or Temple",
        "category": "institutional",
        "compatible_zones": ["D-G", "R-B", "R-I", "R-U"],
        "ministerial": False,
        "description_es": "Lugar de culto religioso",
    },
    {
        "code": "MIX-USE",
        "name_es": "Uso Mixto",
        "name_en": "Mixed Use",
        "category": "mixed",
        "compatible_zones": ["R-C", "C-I", "C-C"],
        "ministerial": False,
        "description_es": "Combinacion de usos residenciales y comerciales",
    },
]

# Embedded data from data/regulations/zoning_districts.json
ZONING_DISTRICTS = [
    {
        "code": "R-B",
        "name_es": "Residencial de Baja Densidad",
        "name_en": "Low Density Residential",
        "category": "residential",
        "description_es": "Desarrollo residencial de baja densidad",
        "min_lot_size": "800 m2",
        "max_height": "2 pisos",
        "max_coverage": "40%",
    },
    {
        "code": "R-I",
        "name_es": "Residencial Intermedio",
        "name_en": "Intermediate Residential",
        "category": "residential",
        "description_es": "Desarrollo residencial de densidad intermedia",
        "min_lot_size": "400 m2",
        "max_height": "3 pisos",
        "max_coverage": "50%",
    },
    {
        "code": "R-U",
        "name_es": "Residencial Urbano",
        "name_en": "Urban Residential",
        "category": "residential",
        "description_es": "Desarrollo residencial urbano de densidad media-alta",
        "min_lot_size": "200 m2",
        "max_height": "4 pisos",
        "max_coverage": "60%",
    },
    {
        "code": "R-C",
        "name_es": "Residencial Comercial",
        "name_en": "Residential Commercial",
        "category": "mixed",
        "description_es": "Uso mixto residencial-comercial",
        "min_lot_size": "200 m2",
        "max_height": "4 pisos",
        "max_coverage": "70%",
    },
    {
        "code": "C-L",
        "name_es": "Comercial Liviano",
        "name_en": "Light Commercial",
        "category": "commercial",
        "description_es": "Comercio de escala vecinal o de barrio",
        "max_coverage": "60%",
        "max_height": "3 pisos",
    },
    {
        "code": "C-I",
        "name_es": "Comercial Intermedio",
        "name_en": "Intermediate Commercial",
        "category": "commercial",
        "description_es": "Comercio de escala intermedia o comunitaria",
        "max_coverage": "70%",
        "max_height": "5 pisos",
    },
    {
        "code": "C-C",
        "name_es": "Comercial Central",
        "name_en": "Central Commercial",
        "category": "commercial",
        "description_es": "Centro comercial o distrito comercial principal",
        "max_coverage": "80%",
        "max_height": "Sin limite",
    },
    {
        "code": "RT-I",
        "name_es": "Residencial Turistico Intermedio",
        "name_en": "Intermediate Tourist Residential",
        "category": "tourist",
        "description_es": "Desarrollo turistico residencial de densidad intermedia",
        "min_lot_size": "300 m2",
        "max_height": "5 pisos",
    },
    {
        "code": "RT-A",
        "name_es": "Residencial Turistico de Alta Densidad",
        "name_en": "High Density Tourist Residential",
        "category": "tourist",
        "description_es": "Desarrollo turistico de alta densidad",
        "min_lot_size": "150 m2",
        "max_height": "8 pisos",
    },
    {
        "code": "C-T",
        "name_es": "Comercial Turistico",
        "name_en": "Tourist Commercial",
        "category": "tourist",
        "description_es": "Comercio orientado al turismo",
        "max_coverage": "70%",
        "max_height": "6 pisos",
    },
    {
        "code": "DTS",
        "name_es": "Desarrollo Turistico Selectivo",
        "name_en": "Selective Tourist Development",
        "category": "tourist",
        "description_es": "Desarrollo turistico con criterios selectivos",
    },
    {
        "code": "I-L",
        "name_es": "Industrial Liviano",
        "name_en": "Light Industrial",
        "category": "industrial",
        "description_es": "Industria liviana con bajo impacto ambiental",
        "max_coverage": "70%",
    },
    {
        "code": "I-P",
        "name_es": "Industrial Pesado",
        "name_en": "Heavy Industrial",
        "category": "industrial",
        "description_es": "Industria pesada o de alto impacto",
        "max_coverage": "75%",
    },
    {
        "code": "I-E",
        "name_es": "Industria Especializada",
        "name_en": "Specialized Industry",
        "category": "industrial",
        "description_es": "Industria de tecnologia o manufactura especializada",
    },
    {
        "code": "A-G",
        "name_es": "Agricola General",
        "name_en": "General Agricultural",
        "category": "agricultural",
        "description_es": "Uso agricola general y actividades relacionadas",
        "min_lot_size": "2000 m2",
        "max_coverage": "20%",
    },
    {
        "code": "A-P",
        "name_es": "Agricola Productivo",
        "name_en": "Productive Agricultural",
        "category": "agricultural",
        "description_es": "Suelos de alto valor agricola para produccion",
        "min_lot_size": "3000 m2",
        "max_coverage": "15%",
    },
    {
        "code": "R-G",
        "name_es": "Rural General",
        "name_en": "General Rural",
        "category": "rural",
        "description_es": "Uso rural general con actividades agricolas y residenciales",
        "min_lot_size": "2000 m2",
        "max_coverage": "25%",
    },
    {
        "code": "ARD",
        "name_es": "Area Rural Desarrollada",
        "name_en": "Developed Rural Area",
        "category": "rural",
        "description_es": "Area rural con desarrollo existente",
        "min_lot_size": "1000 m2",
    },
    {
        "code": "D-G",
        "name_es": "Dotacional General",
        "name_en": "General Institutional",
        "category": "institutional",
        "description_es": "Usos institucionales, educativos, de salud y servicios publicos",
    },
]

# Puerto Rico municipalities
MUNICIPALITIES = [
    "Adjuntas", "Aguada", "Aguadilla", "Aguas Buenas", "Aibonito",
    "Anasco", "Arecibo", "Arroyo", "Barceloneta", "Barranquitas",
    "Bayamon", "Cabo Rojo", "Caguas", "Camuy", "Canovanas",
    "Carolina", "Catano", "Cayey", "Ceiba", "Ciales",
    "Cidra", "Coamo", "Comerio", "Corozal", "Culebra",
    "Dorado", "Fajardo", "Florida", "Guanica", "Guayama",
    "Guayanilla", "Guaynabo", "Gurabo", "Hatillo", "Hormigueros",
    "Humacao", "Isabela", "Jayuya", "Juana Diaz", "Juncos",
    "Lajas", "Lares", "Las Marias", "Las Piedras", "Loiza",
    "Luquillo", "Manati", "Maricao", "Maunabo", "Mayaguez",
    "Moca", "Morovis", "Naguabo", "Naranjito", "Orocovis",
    "Patillas", "Penuelas", "Ponce", "Quebradillas", "Rincon",
    "Rio Grande", "Sabana Grande", "Salinas", "San German", "San Juan",
    "San Lorenzo", "San Sebastian", "Santa Isabel", "Toa Alta", "Toa Baja",
    "Trujillo Alto", "Utuado", "Vega Alta", "Vega Baja", "Vieques",
    "Villalba", "Yabucoa", "Yauco"
]


class RulesDatabase:
    """Load and manage regulatory data"""

    def __init__(self):
        self._use_types = USE_TYPES
        self._zoning_districts = ZONING_DISTRICTS
        self._municipalities = MUNICIPALITIES

    def get_municipalities(self) -> List[str]:
        """Get list of all municipalities"""
        return self._municipalities

    def get_zoning_districts(self) -> List[Dict]:
        """Get all zoning districts"""
        return self._zoning_districts

    def get_zoning_district(self, code: str) -> Optional[Dict]:
        """Get specific zoning district by code"""
        for district in self._zoning_districts:
            if district["code"] == code:
                return district
        return None

    def get_use_types(self) -> List[Dict]:
        """Get all use types"""
        return self._use_types

    def get_use_type(self, code: str) -> Optional[Dict]:
        """Get specific use type by code"""
        for use in self._use_types:
            if use["code"] == code:
                return use
        return None


@lru_cache()
def get_rules_db() -> RulesDatabase:
    """Get cached rules database instance"""
    return RulesDatabase()
