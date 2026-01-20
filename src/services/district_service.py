import json
from pathlib import Path
from typing import List, Dict, Optional

class DistrictService:
    """Service for managing POT and RC district codes"""

    def __init__(self):
        pot_file = Path(__file__).parent.parent.parent / "data" / "regulations" / "pot_districts.json"
        with open(pot_file, 'r', encoding='utf-8') as f:
            self.pot_data = json.load(f)

    def get_districts_for_municipality(self, municipality: str) -> List[Dict]:
        """
        Returns list of districts for a given municipality

        Returns:
            [
                {"code": "R-2", "name": "Residencial Intermedio", "rc_equivalents": ["R-I"], "is_pot": False},
                ...
            ]
        """

        if municipality in self.pot_data['municipalities_with_pot']:
            # POT municipality - return POT districts
            pot_districts = self.pot_data['pot_districts'][municipality]['districts']

            return [
                {
                    "code": d['code'],
                    "name": d.get('description', d['code']),
                    "rc_equivalents": d.get('rc_equivalents', [d['code']]),
                    "is_pot": True
                }
                for d in pot_districts
            ]

        else:
            # Standard RC municipality
            return [
                {
                    "code": d['code'],
                    "name": d['name'],
                    "rc_equivalents": [d['code']],
                    "is_pot": False
                }
                for d in self.pot_data['standard_rc_districts']
            ]

    def get_rc_equivalent(self, pot_code: str, municipality: str) -> str:
        """Converts POT code to RC equivalent (returns first equivalent for backwards compatibility)"""
        equivalents = self.get_rc_equivalents(pot_code, municipality)
        return equivalents[0] if equivalents else pot_code

    def get_rc_equivalents(self, pot_code: str, municipality: str) -> List[str]:
        """
        Returns ALL RC equivalences for a POT code as a list.

        Args:
            pot_code: The POT district code (e.g., "CUT-8")
            municipality: The municipality name

        Returns:
            List of RC equivalent codes (e.g., ["R-U", "R-C", "C-L", "C-I", "D-G", "S-H"])
        """
        if municipality not in self.pot_data['municipalities_with_pot']:
            return [pot_code]  # Already RC code

        pot_districts = self.pot_data['pot_districts'][municipality]['districts']

        for district in pot_districts:
            if district['code'] == pot_code:
                return district.get('rc_equivalents', [pot_code])

        return [pot_code]  # Fallback

    def is_pot_municipality(self, municipality: str) -> bool:
        """Check if municipality has POT"""
        return municipality in self.pot_data['municipalities_with_pot']

    def get_municipalities_with_pot(self) -> List[str]:
        """Get list of municipalities with POT"""
        return self.pot_data['municipalities_with_pot']

    def validate_calificacion(self, calificacion: str, municipality: str) -> dict:
        """
        Validates calificacion format and checks if it's a POT-specific code

        Returns:
            {
                "valid": bool,
                "is_pot": bool,
                "rc_equivalents": List[str] or None,
                "message": str
            }
        """
        # Clean input
        cal = calificacion.strip().upper()

        if not cal:
            return {
                "valid": False,
                "is_pot": False,
                "rc_equivalents": None,
                "message": "Por favor ingresa una calificacion"
            }

        # Check if municipality has POT
        if municipality in self.pot_data['municipalities_with_pot']:
            # Look for POT district match
            pot_districts = self.pot_data['pot_districts'][municipality]['districts']

            for district in pot_districts:
                if district['code'].upper() == cal:
                    return {
                        "valid": True,
                        "is_pot": True,
                        "rc_equivalents": district.get('rc_equivalents', [district['code']]),
                        "message": f"Calificacion POT valida para {municipality}"
                    }

            # Check if it's a standard RC code (user might have entered RC equivalent)
            standard_codes = [d['code'] for d in self.pot_data['standard_rc_districts']]
            if cal in standard_codes:
                return {
                    "valid": True,
                    "is_pot": False,
                    "rc_equivalents": [cal],
                    "message": f"Codigo RC estandar detectado. {municipality} tiene POT - considera usar codigo POT."
                }

            return {
                "valid": False,
                "is_pot": False,
                "rc_equivalents": None,
                "message": f"Calificacion '{calificacion}' no encontrada en POT de {municipality}. Verifica el codigo."
            }

        else:
            # Standard RC municipality
            standard_codes = [d['code'] for d in self.pot_data['standard_rc_districts']]

            if cal in standard_codes:
                return {
                    "valid": True,
                    "is_pot": False,
                    "rc_equivalents": [cal],
                    "message": "Calificacion RC valida"
                }
            else:
                return {
                    "valid": False,
                    "is_pot": False,
                    "rc_equivalents": None,
                    "message": f"Calificacion '{calificacion}' no reconocida. Verifica el codigo."
                }
