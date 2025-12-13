#Load regulatory data
import json
from pathlib import Path
from typing import Dict, List

class RulesDatabase:
    """Load and manage regulatory data"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.regulations_dir = self.data_dir / "regulations"
        
        # Load all data
        self.municipalities = self._load_json("municipalities.json")
        self.zoning_districts = self._load_json("regulations/zoning_districts.json")
        self.use_types = self._load_json("regulations/use_classifications.json")
        self.tomo6_rules = self._load_json("regulations/tomo6_rules.json")
    
    def _load_json(self, filename: str) -> Dict:
        """Load JSON file from data directory"""
        filepath = self.data_dir / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_municipalities(self) -> List[str]:
        """Get list of all municipalities"""
        return self.municipalities["municipalities"]
    
    def get_zoning_districts(self) -> List[Dict]:
        """Get all zoning districts"""
        return self.zoning_districts["zoning_districts"]
    
    def get_zoning_district(self, code: str) -> Dict:
        """Get specific zoning district by code"""
        for district in self.zoning_districts["zoning_districts"]:
            if district["code"] == code:
                return district
        return None
    
    def get_use_types(self) -> List[Dict]:
        """Get all use types"""
        return self.use_types["use_types"]
    
    def get_use_type(self, code: str) -> Dict:
        """Get specific use type by code"""
        for use in self.use_types["use_types"]:
            if use["code"] == code:
                return use
        return None
    
    def get_use_by_name(self, name: str) -> Dict:
        """Search use by name (Spanish or English)"""
        name_lower = name.lower()
        for use in self.use_types["use_types"]:
            if (name_lower in use["name_es"].lower() or 
                name_lower in use["name_en"].lower()):
                return use
        return None
    
    def get_tomo6_rules(self) -> Dict:
        """Get Tomo 6 validation rules"""
        return self.tomo6_rules["tomo6_rules"]
