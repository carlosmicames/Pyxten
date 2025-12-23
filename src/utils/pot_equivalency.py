"""
POT Equivalency Table Handler
Maps municipal POT districts to Reglamento Conjunto 2023 districts

Based on Tabla 6.1 del Reglamento Conjunto
"""

from typing import Dict, Optional, List


class POTEquivalencyTable:
    """
    Handles district equivalencies between municipal POTs and Reglamento Conjunto
    
    Based on Tabla 6.1 - Evolution of zoning districts:
    Previo 2008 → 2010 → 2020 (Current)
    """
    
    def __init__(self):
        # Load equivalency mappings from Tabla 6.1
        self.equivalencies = self._build_equivalency_table()
    
    def _build_equivalency_table(self) -> Dict[str, Dict]:
        """
        Builds the complete equivalency table from Tabla 6.1
        
        Structure:
        {
            "R-1": {
                "rc_2020": "R-B",
                "rc_2010": "U-R",
                "name_es": "Residencial de Baja Densidad",
                "category": "residential"
            },
            ...
        }
        """
        
        return {
            # RESIDENCIALES
            "R-0": {
                "rc_2020": "R-B",
                "rc_2010": "U-R",
                "name_es": "Residencial de Baja Densidad",
                "category": "residential",
                "notes": "Terrenos Urbanizables"
            },
            "R-1": {
                "rc_2020": "R-B",
                "rc_2010": "U-R",
                "name_es": "Residencial de Baja Densidad",
                "category": "residential"
            },
            "R-2": {
                "rc_2020": "R-I",
                "rc_2010": "R-I",
                "name_es": "Residencial Intermedio",
                "category": "residential"
            },
            "R-3": {
                "rc_2020": "R-I",
                "rc_2010": "R-I",
                "name_es": "Residencial Intermedio",
                "category": "residential"
            },
            "R-4": {
                "rc_2020": "R-U",
                "rc_2010": "R-A",
                "name_es": "Residencial Urbano",
                "category": "residential"
            },
            "R-5": {
                "rc_2020": "R-U",
                "rc_2010": "R-A",
                "name_es": "Residencial Urbano",
                "category": "residential"
            },
            "R-6": {
                "rc_2020": "R-U",
                "rc_2010": "R-ZH",
                "name_es": "Residencial Urbano / Zona Histórica",
                "category": "residential"
            },
            "RC-1": {
                "rc_2020": "R-C",
                "rc_2010": "RC-M",
                "name_es": "Residencia Comercial",
                "category": "residential"
            },
            
            # COMERCIALES
            "C0-1": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial"
            },
            "C-L": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial"
            },
            "C-6": {
                "rc_2020": "C-L",
                "rc_2010": "C-L",
                "name_es": "Comercial Liviano",
                "category": "commercial"
            },
            "C0-2": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial"
            },
            "C-1": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial"
            },
            "C-2": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial"
            },
            "C-3": {
                "rc_2020": "C-I",
                "rc_2010": "C-I",
                "name_es": "Comercial Intermedio",
                "category": "commercial"
            },
            "C-4": {
                "rc_2020": "C-C",
                "rc_2010": "C-C",
                "name_es": "Comercial Central",
                "category": "commercial"
            },
            "C-5": {
                "rc_2020": "RC-E",
                "rc_2010": "RC-E",
                "name_es": "Recreación Comercial Extensa",
                "category": "commercial"
            },
            
            # TURISTICOS
            "RT-1": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turístico Intermedio",
                "category": "tourist"
            },
            "RT-2": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turístico Intermedio",
                "category": "tourist"
            },
            "RT-3": {
                "rc_2020": "RT-I",
                "rc_2010": "RT-I",
                "name_es": "Residencial Turístico Intermedio",
                "category": "tourist"
            },
            "RT-4": {
                "rc_2020": "RT-A",
                "rc_2010": "RT-A",
                "name_es": "Residencial Turístico de Alta Densidad",
                "category": "tourist"
            },
            "RT-5": {
                "rc_2020": "RT-A",
                "rc_2010": "RT-A",
                "name_es": "Residencial Turístico de Alta Densidad",
                "category": "tourist"
            },
            "CT-1": {
                "rc_2020": "C-T",
                "rc_2010": "CT-L",
                "name_es": "Comercial Turístico",
                "category": "tourist"
            },
            "CT-2": {
                "rc_2020": "C-T",
                "rc_2010": "CT-L",
                "name_es": "Comercial Turístico",
                "category": "tourist"
            },
            "CT-3": {
                "rc_2020": "C-T",
                "rc_2010": "CT-I",
                "name_es": "Comercial Turístico",
                "category": "tourist"
            },
            "CT-4": {
                "rc_2020": "C-T",
                "rc_2010": "CT-I",
                "name_es": "Comercial Turístico",
                "category": "tourist"
            },
            "RT-0": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turístico Selectivo",
                "category": "tourist"
            },
            "RT-00": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turístico Selectivo",
                "category": "tourist"
            },
            "DT": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turístico Selectivo",
                "category": "tourist"
            },
            "DTS": {
                "rc_2020": "DTS",
                "rc_2010": "DTS",
                "name_es": "Desarrollo Turístico Selectivo",
                "category": "tourist"
            },
            
            # INDUSTRIALES
            "I-1": {
                "rc_2020": "I-L",
                "rc_2010": "I-L",
                "name_es": "Industrial Liviano",
                "category": "industrial"
            },
            "IL-1": {
                "rc_2020": "I-L",
                "rc_2010": "I-L",
                "name_es": "Industrial Liviano",
                "category": "industrial"
            },
            "I-2": {
                "rc_2020": "I-P",
                "rc_2010": "I-P",
                "name_es": "Industrial Pesado",
                "category": "industrial"
            },
            "IL-2": {
                "rc_2020": "I-P",
                "rc_2010": "I-P",
                "name_es": "Industrial Pesado",
                "category": "industrial"
            },
            "I-E": {
                "rc_2020": "I-E",
                "rc_2010": "I-E",
                "name_es": "Industria Especializada",
                "category": "industrial"
            },
            
            # RURALES/AGRICOLAS
            "AD": {
                "rc_2020": "ARD",
                "rc_2010": "A-D",
                "name_es": "Área Rural Desarrollada",
                "category": "agricultural"
            },
            "A-4": {
                "rc_2020": "R-G",
                "rc_2010": "R-G",
                "name_es": "Rural General",
                "category": "agricultural"
            },
            "A-3": {
                "rc_2020": "A-G",
                "rc_2010": "A-G",
                "name_es": "Agrícola General",
                "category": "agricultural"
            },
            "A-2": {
                "rc_2020": "A-G",
                "rc_2010": "A-G",
                "name_es": "Agrícola General",
                "category": "agricultural"
            },
            "AR-2": {
                "rc_2020": "A-G",
                "rc_2010": "AR-2",
                "name_es": "Agrícola en Reserva Dos",
                "category": "agricultural"
            },
            "A-1": {
                "rc_2020": "A-P",
                "rc_2010": "A-P",
                "name_es": "Agrícola Productiva",
                "category": "agricultural"
            },
            "AR-1": {
                "rc_2020": "A-P",
                "rc_2010": "AR-1",
                "name_es": "Agrícola en Reserva Una",
                "category": "agricultural"
            },
            "PM": {
                "rc_2020": "A-G",
                "rc_2010": "P-M",
                "name_es": "Pesca y Maricultura",
                "category": "agricultural"
            },
            
            # DOTACIONALES
            "P": {
                "rc_2020": "D-G",
                "rc_2010": "DT-G",
                "name_es": "Dotacional General",
                "category": "dotational"
            },
            "B-1": {
                "rc_2020": "D-A",
                "rc_2010": "B-Q",
                "name_es": "Dotacional Área Abierta / Bosque",
                "category": "conservation"
            },
            "B-3": {
                "rc_2020": "D-A",
                "rc_2010": "B-Q",
                "name_es": "Dotacional Área Abierta / Bosque",
                "category": "conservation"
            },
            "PR": {
                "rc_2020": "P-R",
                "rc_2010": "P-R",
                "name_es": "Preservación de Recursos",
                "category": "conservation"
            },
            "B-2": {
                "rc_2020": "P-R",
                "rc_2010": "P-R",
                "name_es": "Preservación de Recursos",
                "category": "conservation"
            },
            "RE": {
                "rc_2020": "R-E",
                "rc_2010": "R-E",
                "name_es": "Reserva Escénica",
                "category": "conservation"
            },
            "PP": {
                "rc_2020": "P-P",
                "rc_2010": "P-P",
                "name_es": "Parque Público",
                "category": "conservation"
            },
            
            # HISTORICOS/ESPECIALES
            "CR-H": {
                "rc_2020": "S-H",
                "rc_2010": "S-H",
                "name_es": "Suelo Histórico",
                "category": "historical"
            },
            "CR-1": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservación de Recursos",
                "category": "conservation"
            },
            "CR-2": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservación de Recursos",
                "category": "conservation"
            },
            "CR-3": {
                "rc_2020": "C-R",
                "rc_2010": "CR-C",
                "name_es": "Conservación de Recursos",
                "category": "conservation"
            },
            "CR-4": {
                "rc_2020": "C-R",
                "rc_2010": "CR",
                "name_es": "Conservación de Recursos",
                "category": "conservation"
            },
        }
    
    def get_rc_equivalent(
        self,
        pot_district: str,
        year: str = "2020"
    ) -> Optional[Dict]:
        """
        Get Reglamento Conjunto equivalent for a POT district
        
        Args:
            pot_district: Municipal POT district code (e.g., "R-2", "C-1")
            year: RC version - "2020" (current) or "2010"
        
        Returns:
            {
                "rc_code": "R-I",
                "rc_name": "Residencial Intermedio",
                "category": "residential",
                "original_pot_code": "R-2",
                "notes": "..."
            }
        """
        
        # Normalize district code
        pot_district = pot_district.strip().upper()
        
        # Check if exists in table
        if pot_district not in self.equivalencies:
            return None
        
        equiv = self.equivalencies[pot_district]
        
        # Get RC code for specified year
        rc_code_key = f"rc_{year}"
        rc_code = equiv.get(rc_code_key)
        
        if not rc_code:
            return None
        
        return {
            "rc_code": rc_code,
            "rc_name": equiv["name_es"],
            "category": equiv["category"],
            "original_pot_code": pot_district,
            "notes": equiv.get("notes", ""),
            "equivalency_year": year
        }
    
    def get_all_equivalents(self, pot_district: str) -> Dict:
        """
        Get all equivalents (2010 and 2020) for a POT district
        """
        
        pot_district = pot_district.strip().upper()
        
        if pot_district not in self.equivalencies:
            return {
                "found": False,
                "original_code": pot_district
            }
        
        return {
            "found": True,
            "original_code": pot_district,
            "rc_2020": self.get_rc_equivalent(pot_district, "2020"),
            "rc_2010": self.get_rc_equivalent(pot_district, "2010"),
            "evolution": self.equivalencies[pot_district]
        }
    
    def is_municipal_specific(self, district_code: str) -> bool:
        """
        Check if a district code is municipal-specific (needs equivalency)
        vs. already using RC 2020 codes
        """
        
        district_code = district_code.strip().upper()
        
        # RC 2020 codes that don't need translation
        rc_2020_codes = {
            "R-B", "R-I", "R-U", "R-C",
            "C-L", "C-I", "C-C", "C-T", "RC-E",
            "RT-I", "RT-A", "DTS",
            "I-L", "I-P", "I-E",
            "ARD", "R-G", "A-G", "A-P",
            "D-G", "D-A",
            "A-B", "C-R", "P-R", "R-E", "P-P",
            "S-H", "C-H", "M", "R-EA"
        }
        
        return district_code not in rc_2020_codes
    
    def get_suggested_districts(self, category: str) -> List[Dict]:
        """
        Get all districts in a category
        
        Useful for showing user alternatives
        """
        
        results = []
        
        for pot_code, data in self.equivalencies.items():
            if data["category"] == category:
                equiv = self.get_rc_equivalent(pot_code, "2020")
                if equiv:
                    results.append(equiv)
        
        # Remove duplicates (multiple POT codes map to same RC code)
        seen = set()
        unique_results = []
        
        for r in results:
            if r["rc_code"] not in seen:
                seen.add(r["rc_code"])
                unique_results.append(r)
        
        return unique_results


# Example usage
if __name__ == "__main__":
    table = POTEquivalencyTable()
    
    # Example: Old POT code
    print("R-2 equivalency:")
    print(table.get_rc_equivalent("R-2", "2020"))
    
    print("\nAll equivalents for R-2:")
    print(table.get_all_equivalents("R-2"))
    
    print("\nIs 'R-2' municipal-specific?", table.is_municipal_specific("R-2"))
    print("Is 'R-I' municipal-specific?", table.is_municipal_specific("R-I"))
    
    print("\nAll residential districts:")
    for dist in table.get_suggested_districts("residential"):
        print(f"  {dist['rc_code']}: {dist['rc_name']}")