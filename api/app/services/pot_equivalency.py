"""
POT Equivalency Table Handler
Maps municipal POT districts to Reglamento Conjunto 2023 districts
Ported from src/utils/pot_equivalency.py
"""
from typing import Dict, Optional, List


class POTEquivalencyTable:
    """
    Handles district equivalencies between municipal POTs and Reglamento Conjunto

    Based on Tabla 6.1 - Evolution of zoning districts:
    Previo 2008 -> 2010 -> 2020 (Current)
    """

    def __init__(self):
        self.equivalencies = self._build_equivalency_table()

    def _build_equivalency_table(self) -> Dict[str, Dict]:
        """Build the complete equivalency table from Tabla 6.1"""
        return {
            # RESIDENCIALES
            "R-0": {
                "rc_2020": "R-B",
                "rc_2010": "U-R",
                "name_es": "Residencial de Baja Densidad",
                "category": "residential",
            },
            "R-1": {
                "rc_2020": "R-B",
                "rc_2010": "U-R",
                "name_es": "Residencial de Baja Densidad",
                "category": "residential",
            },
            "R-2": {
                "rc_2020": "R-I",
                "rc_2010": "R-I",
                "name_es": "Residencial Intermedio",
                "category": "residential",
            },
            "R-3": {
                "rc_2020": "R-I",
                "rc_2010": "R-I",
                "name_es": "Residencial Intermedio",
                "category": "residential",
            },
            "R-4": {
                "rc_2020": "R-U",
                "rc_2010": "R-A",
                "name_es": "Residencial Urbano",
                "category": "residential",
            },
            "R-5": {
                "rc_2020": "R-U",
                "rc_2010": "R-A",
                "name_es": "Residencial Urbano",
                "category": "residential",
            },
            "R-6": {
                "rc_2020": "R-U",
                "rc_2010": "R-ZH",
                "name_es": "Residencial Urbano / Zona Historica",
                "category": "residential",
            },
            "RC-1": {
                "rc_2020": "R-C",
                "rc_2010": "RC-M",
                "name_es": "Residencia Comercial",
                "category": "residential",
            },
            # COMERCIALES
            "C0-1": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial",
            },
            "C-L": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial",
            },
            "C-6": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial",
            },
            "C0-2": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial",
            },
            "C-1": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial",
            },
            "C-2": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial",
            },
            "C-3": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial",
            },
            "C-4": {
                "rc_2020": "C-C",
                "rc_2010": "C-C",
                "name_es": "Comercial Central",
                "category": "commercial",
            },
            "C-5": {
                "rc_2020": "RC-E",
                "rc_2010": "RC-E",
                "name_es": "Recreacion Comercial Extensa",
                "category": "commercial",
            },
            # TURISTICOS
            "RT-1": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turistico Intermedio",
                "category": "tourist",
            },
            "RT-2": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turistico Intermedio",
                "category": "tourist",
            },
            "RT-3": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turistico Intermedio",
                "category": "tourist",
            },
            "RT-4": {
                "rc_2020": "RT-A",
                "rc_2010": "RT-A",
                "name_es": "Residencial Turistico de Alta Densidad",
                "category": "tourist",
            },
            "RT-5": {
                "rc_2020": "RT-A",
                "rc_2010": "RT-A",
                "name_es": "Residencial Turistico de Alta Densidad",
                "category": "tourist",
            },
            "CT-1": {
                "rc_2020": "C-T",
                "rc_2010": "CT-L",
                "name_es": "Comercial Turistico",
                "category": "tourist",
            },
            "CT-2": {
                "rc_2020": "C-T",
                "rc_2010": "CT-L",
                "name_es": "Comercial Turistico",
                "category": "tourist",
            },
            "CT-3": {
                "rc_2020": "C-T",
                "rc_2010": "CT-I",
                "name_es": "Comercial Turistico",
                "category": "tourist",
            },
            "CT-4": {
                "rc_2020": "C-T",
                "rc_2010": "CT-I",
                "name_es": "Comercial Turistico",
                "category": "tourist",
            },
            "RT-0": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turistico Selectivo",
                "category": "tourist",
            },
            "DT": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turistico Selectivo",
                "category": "tourist",
            },
            "DTS": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turistico Selectivo",
                "category": "tourist",
            },
            # INDUSTRIALES
            "I-1": {
                "rc_2020": "I-L",
                "rc_2010": "I-L",
                "name_es": "Industrial Liviano",
                "category": "industrial",
            },
            "IL-1": {
                "rc_2020": "I-L",
                "rc_2010": "I-L",
                "name_es": "Industrial Liviano",
                "category": "industrial",
            },
            "I-2": {
                "rc_2020": "I-P",
                "rc_2010": "I-P",
                "name_es": "Industrial Pesado",
                "category": "industrial",
            },
            "IL-2": {
                "rc_2020": "I-P",
                "rc_2010": "I-P",
                "name_es": "Industrial Pesado",
                "category": "industrial",
            },
            "I-E": {
                "rc_2020": "I-E",
                "rc_2010": "I-E",
                "name_es": "Industria Especializada",
                "category": "industrial",
            },
            # RURALES/AGRICOLAS
            "AD": {
                "rc_2020": "ARD",
                "rc_2010": "A-D",
                "name_es": "Area Rural Desarrollada",
                "category": "agricultural",
            },
            "A-4": {
                "rc_2020": "R-G",
                "rc_2010": "R-G",
                "name_es": "Rural General",
                "category": "agricultural",
            },
            "A-3": {
                "rc_2020": "A-G",
                "rc_2010": "A-G",
                "name_es": "Agricola General",
                "category": "agricultural",
            },
            "A-2": {
                "rc_2020": "A-G",
                "rc_2010": "A-G",
                "name_es": "Agricola General",
                "category": "agricultural",
            },
            "AR-2": {
                "rc_2020": "A-G",
                "rc_2010": "AR-2",
                "name_es": "Agricola en Reserva Dos",
                "category": "agricultural",
            },
            "A-1": {
                "rc_2020": "A-P",
                "rc_2010": "A-P",
                "name_es": "Agricola Productiva",
                "category": "agricultural",
            },
            "AR-1": {
                "rc_2020": "A-P",
                "rc_2010": "AR-1",
                "name_es": "Agricola en Reserva Una",
                "category": "agricultural",
            },
            "PM": {
                "rc_2020": "A-G",
                "rc_2010": "P-M",
                "name_es": "Pesca y Maricultura",
                "category": "agricultural",
            },
            # DOTACIONALES
            "P": {
                "rc_2020": "D-G",
                "rc_2010": "DT-G",
                "name_es": "Dotacional General",
                "category": "dotational",
            },
            "B-1": {
                "rc_2020": "D-A",
                "rc_2010": "B-Q",
                "name_es": "Dotacional Area Abierta / Bosque",
                "category": "conservation",
            },
            "B-3": {
                "rc_2020": "D-A",
                "rc_2010": "B-Q",
                "name_es": "Dotacional Area Abierta / Bosque",
                "category": "conservation",
            },
            "PR": {
                "rc_2020": "P-R",
                "rc_2010": "P-R",
                "name_es": "Preservacion de Recursos",
                "category": "conservation",
            },
            "B-2": {
                "rc_2020": "P-R",
                "rc_2010": "P-R",
                "name_es": "Preservacion de Recursos",
                "category": "conservation",
            },
            "RE": {
                "rc_2020": "R-E",
                "rc_2010": "R-E",
                "name_es": "Reserva Escenica",
                "category": "conservation",
            },
            "PP": {
                "rc_2020": "P-P",
                "rc_2010": "P-P",
                "name_es": "Parque Publico",
                "category": "conservation",
            },
            # HISTORICOS/ESPECIALES
            "CR-H": {
                "rc_2020": "S-H",
                "rc_2010": "S-H",
                "name_es": "Suelo Historico",
                "category": "historical",
            },
            "CR-1": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservacion de Recursos",
                "category": "conservation",
            },
            "CR-2": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservacion de Recursos",
                "category": "conservation",
            },
            "CR-3": {
                "rc_2020": "C-R",
                "rc_2010": "CR-C",
                "name_es": "Conservacion de Recursos",
                "category": "conservation",
            },
            "CR-4": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservacion de Recursos",
                "category": "conservation",
            },
        }

    def get_rc_equivalent(
        self, pot_district: str, year: str = "2020"
    ) -> Optional[Dict]:
        """Get Reglamento Conjunto equivalent for a POT district"""
        pot_district = pot_district.strip().upper()

        if pot_district not in self.equivalencies:
            return None

        equiv = self.equivalencies[pot_district]
        rc_code_key = f"rc_{year}"
        rc_code = equiv.get(rc_code_key)

        if not rc_code:
            return None

        return {
            "rc_code": rc_code,
            "rc_name": equiv["name_es"],
            "category": equiv["category"],
            "original_pot_code": pot_district,
            "equivalency_year": year,
        }

    def is_municipal_specific(self, district_code: str) -> bool:
        """Check if a district code is municipal-specific (needs equivalency)"""
        district_code = district_code.strip().upper()

        # RC 2020 codes that don't need translation
        rc_2020_codes = {
            "R-B",
            "R-I",
            "R-U",
            "R-C",
            "C-L",
            "C-I",
            "C-C",
            "C-T",
            "RC-E",
            "RT-I",
            "RT-A",
            "DTS",
            "I-L",
            "I-P",
            "I-E",
            "ARD",
            "R-G",
            "A-G",
            "A-P",
            "D-G",
            "D-A",
            "A-B",
            "C-R",
            "P-R",
            "R-E",
            "P-P",
            "S-H",
            "C-H",
            "M",
            "R-EA",
        }

        return district_code not in rc_2020_codes
