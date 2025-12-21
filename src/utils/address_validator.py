"""
AddressValidator - Valida direcciones usando Google Maps Geocoding API
"""

import os
import requests
from typing import Dict, Optional

class AddressValidator:
    """Valida direcciones de Puerto Rico con Google Maps API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY no encontrada en .env")
        
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def validate_address(
        self, 
        address: str, 
        municipality: str,
        country: str = "Puerto Rico"
    ) -> Dict:
        """
        Valida dirección usando Google Geocoding API
        
        Args:
            address: Dirección (ej: "Calle Luna 123")
            municipality: Municipio (ej: "San Juan")
            country: País (default: "Puerto Rico")
        
        Returns:
            {
                "valid": bool,
                "formatted_address": str,
                "latitude": float,
                "longitude": float,
                "place_id": str,
                "confidence": str,  # "ROOFTOP", "RANGE_INTERPOLATED", etc.
                "components": {...},
                "error": str (si aplica)
            }
        """
        
        # Construir dirección completa
        full_address = f"{address}, {municipality}, {country}"
        
        try:
            # Llamar a Geocoding API
            response = requests.get(
                self.geocoding_url,
                params={
                    "address": full_address,
                    "key": self.api_key,
                    "region": "pr",  # Bias hacia Puerto Rico
                    "language": "es"
                },
                timeout=10
            )
            
            data = response.json()
            
            # Verificar status
            if data["status"] != "OK":
                return {
                    "valid": False,
                    "error": f"Google Maps API error: {data['status']}",
                    "formatted_address": full_address
                }
            
            # Obtener primer resultado (mejor match)
            result = data["results"][0]
            
            # Extraer datos
            location = result["geometry"]["location"]
            components = self._parse_address_components(result["address_components"])
            
            # Validar que es de Puerto Rico
            if components.get("country") != "Puerto Rico":
                return {
                    "valid": False,
                    "error": "Dirección no es de Puerto Rico",
                    "formatted_address": result["formatted_address"]
                }
            
            # Validar que municipio coincide (flexible)
            if municipality.lower() not in result["formatted_address"].lower():
                return {
                    "valid": True,  # Aún válido pero con advertencia
                    "warning": f"Municipio '{municipality}' no coincide exactamente",
                    "formatted_address": result["formatted_address"],
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "place_id": result["place_id"],
                    "confidence": result["geometry"]["location_type"],
                    "components": components
                }
            
            return {
                "valid": True,
                "formatted_address": result["formatted_address"],
                "latitude": location["lat"],
                "longitude": location["lng"],
                "place_id": result["place_id"],
                "confidence": result["geometry"]["location_type"],
                "components": components
            }
            
        except requests.exceptions.Timeout:
            return {
                "valid": False,
                "error": "Timeout conectando con Google Maps API",
                "formatted_address": full_address
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error validando dirección: {str(e)}",
                "formatted_address": full_address
            }
    
    def _parse_address_components(self, components: list) -> Dict:
        """Parsea componentes de dirección de Google"""
        
        parsed = {}
        
        type_map = {
            "street_number": "street_number",
            "route": "route",
            "locality": "city",
            "administrative_area_level_1": "state",
            "country": "country",
            "postal_code": "postal_code"
        }
        
        for component in components:
            for comp_type in component["types"]:
                if comp_type in type_map:
                    key = type_map[comp_type]
                    parsed[key] = component["long_name"]
        
        return parsed
    
    def get_coordinates(self, address: str, municipality: str) -> Optional[tuple]:
        """
        Obtiene coordenadas lat/lng de una dirección
        
        Returns:
            (lat, lng) o None si no válida
        """
        result = self.validate_address(address, municipality)
        
        if result.get("valid"):
            return (result["latitude"], result["longitude"])
        
        return None