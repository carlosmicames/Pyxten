"""
AddressValidator - Validates addresses using Google Maps Geocoding API
Ported from src/utils/address_validator.py
"""
import httpx
from typing import Dict, Optional, Tuple
from app.config import get_settings


class AddressValidator:
    """Validates Puerto Rico addresses with Google Maps API"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.google_maps_api_key
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.client = httpx.Client(timeout=10)

    def validate_address(
        self, address: str, municipality: str, country: str = "Puerto Rico"
    ) -> Dict:
        """
        Validate address using Google Geocoding API

        Args:
            address: Street address
            municipality: Municipality name
            country: Country (default: "Puerto Rico")

        Returns:
            Validation result with coordinates and confidence
        """
        full_address = f"{address}, {municipality}, {country}"

        try:
            response = self.client.get(
                self.geocoding_url,
                params={
                    "address": full_address,
                    "key": self.api_key,
                    "region": "pr",
                    "language": "es",
                },
            )

            data = response.json()

            if data["status"] != "OK":
                return {
                    "valid": False,
                    "error": f"Google Maps API error: {data['status']}",
                    "formatted_address": full_address,
                }

            result = data["results"][0]
            location = result["geometry"]["location"]
            components = self._parse_address_components(result["address_components"])

            # Validate it's in Puerto Rico
            if components.get("country") != "Puerto Rico":
                return {
                    "valid": False,
                    "error": "Direccion no es de Puerto Rico",
                    "formatted_address": result["formatted_address"],
                }

            # Check municipality match
            if municipality.lower() not in result["formatted_address"].lower():
                return {
                    "valid": True,
                    "warning": f"Municipio '{municipality}' no coincide exactamente",
                    "formatted_address": result["formatted_address"],
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "place_id": result["place_id"],
                    "confidence": result["geometry"]["location_type"],
                    "components": components,
                }

            return {
                "valid": True,
                "formatted_address": result["formatted_address"],
                "latitude": location["lat"],
                "longitude": location["lng"],
                "place_id": result["place_id"],
                "confidence": result["geometry"]["location_type"],
                "components": components,
            }

        except httpx.TimeoutException:
            return {
                "valid": False,
                "error": "Timeout conectando con Google Maps API",
                "formatted_address": full_address,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error validando direccion: {str(e)}",
                "formatted_address": full_address,
            }

    def _parse_address_components(self, components: list) -> Dict:
        """Parse Google address components"""
        parsed = {}

        type_map = {
            "street_number": "street_number",
            "route": "route",
            "locality": "city",
            "administrative_area_level_1": "state",
            "country": "country",
            "postal_code": "postal_code",
        }

        for component in components:
            for comp_type in component["types"]:
                if comp_type in type_map:
                    key = type_map[comp_type]
                    parsed[key] = component["long_name"]

        return parsed

    def get_coordinates(
        self, address: str, municipality: str
    ) -> Optional[Tuple[float, float]]:
        """Get lat/lng coordinates for an address"""
        result = self.validate_address(address, municipality)

        if result.get("valid"):
            return (result["latitude"], result["longitude"])

        return None
