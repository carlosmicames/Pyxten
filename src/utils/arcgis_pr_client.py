"""
ArcGIS Client for Puerto Rico Planning Board (MIPR)
Queries zoning, overlays, and parcel data from SIGE/MIPR services
"""

import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ArcGISPRClient:
    """
    Client for Puerto Rico's MIPR (Mapa Interactivo de Puerto Rico) ArcGIS services
    
    Endpoints:
    - Calificación (Zoning): https://sige.pr.gov/server/rest/services/MIPR/Calificacion/MapServer
    - Reglamentario (Overlays): https://sige.pr.gov/server/rest/services/MIPR/Reglamentario/MapServer
    - Parcelas (CRIM): https://sigejp.pr.gov/server/rest/services/crim/crim_parcelas/MapServer
    """
    
    def __init__(self):
        self.calificacion_url = "https://sige.pr.gov/server/rest/services/MIPR/Calificacion/MapServer"
        self.reglamentario_url = "https://sige.pr.gov/server/rest/services/MIPR/Reglamentario/MapServer"
        self.parcelas_url = "https://sigejp.pr.gov/server/rest/services/crim/crim_parcelas/MapServer"
        
        # Timeout for API calls
        self.timeout = 15
        
        # Cache layer IDs (populated on first call)
        self._layer_cache = {}
    
    def get_zoning_at_point(
        self, 
        latitude: float, 
        longitude: float,
        buffer_meters: int = 10
    ) -> Dict:
        """
        Get zoning district at a specific coordinate
        
        Args:
            latitude: Latitude in WGS84 (EPSG:4326)
            longitude: Longitude in WGS84
            buffer_meters: Buffer around point for query (default 10m)
        
        Returns:
            {
                "district_code": "C-L",
                "district_name": "Comercial Liviano",
                "source": "MIPR Calificación",
                "last_updated": "2024-12-15",
                "confidence": "high" | "medium" | "low",
                "raw_data": {...},
                "error": None
            }
        """
        
        try:
            # Get Calificación layer ID (zoning districts)
            layer_id = self._get_layer_id(self.calificacion_url, "Calificación")
            
            if layer_id is None:
                return self._error_response("Could not find Calificación layer")
            
            # Construct query URL
            query_url = f"{self.calificacion_url}/{layer_id}/query"
            
            # Convert WGS84 to Web Mercator (EPSG:3857) for buffer
            # Note: For small areas near PR, simple conversion works
            x, y = self._wgs84_to_web_mercator(longitude, latitude)
            
            # Query parameters
            params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": "3857",  # Web Mercator
                "spatialRel": "esriSpatialRelIntersects",
                "distance": buffer_meters,
                "units": "esriSRUnit_Meter",
                "outFields": "*",  # Get all fields
                "returnGeometry": "false",
                "f": "json"
            }
            
            response = requests.get(query_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for features
            if not data.get("features"):
                return self._error_response(
                    "No zoning district found at this location",
                    confidence="low"
                )
            
            # Get first feature (closest match)
            feature = data["features"][0]
            attributes = feature["attributes"]
            
            # Extract zoning info
            # Fields: 'cali' (code) and 'descrip' (description)
            district_code = attributes.get("cali", "").strip()
            district_name = attributes.get("descrip", "").strip()
            
            # Get metadata if available
            last_updated = attributes.get("fecha_actualizacion") or attributes.get("last_edited_date")
            source_agency = attributes.get("fuente") or "MIPR"
            
            return {
                "district_code": district_code,
                "district_name": district_name,
                "source": f"{source_agency} Calificación",
                "last_updated": self._parse_date(last_updated),
                "confidence": "high" if district_code else "low",
                "municipality": attributes.get("municipio", ""),
                "raw_data": attributes,
                "error": None
            }
            
        except requests.exceptions.Timeout:
            return self._error_response("MIPR service timeout - try again")
        except requests.exceptions.RequestException as e:
            logger.error(f"ArcGIS API error: {e}")
            return self._error_response(f"Error querying MIPR: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_zoning_at_point: {e}")
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def get_overlay_zones(
        self,
        latitude: float,
        longitude: float,
        buffer_meters: int = 10
    ) -> List[Dict]:
        """
        Get overlay zones at a specific coordinate
        
        Returns list of overlays:
        [
            {
                "overlay_type": "Zona Histórica",
                "description": "...",
                "source": "MIPR Reglamentario",
                "restrictions": {...}
            },
            ...
        ]
        """
        
        overlays = []
        
        try:
            # Query Reglamentario service for overlays
            # This service has multiple layers for different overlay types
            
            overlay_layers = [
                ("Zona Histórica", "zona_historica"),
                ("Zona Costanera", "zona_costanera"),
                ("Áreas Especiales de Riesgo a Inundación", "area_inundacion"),
                ("Revisión Mapa de FEMA", "fema"),
            ]
            
            x, y = self._wgs84_to_web_mercator(longitude, latitude)
            
            for overlay_name, layer_name in overlay_layers:
                try:
                    layer_id = self._get_layer_id(self.reglamentario_url, layer_name)
                    
                    if layer_id is None:
                        continue
                    
                    query_url = f"{self.reglamentario_url}/{layer_id}/query"
                    
                    params = {
                        "geometry": f"{x},{y}",
                        "geometryType": "esriGeometryPoint",
                        "inSR": "3857",
                        "spatialRel": "esriSpatialRelIntersects",
                        "distance": buffer_meters,
                        "units": "esriSRUnit_Meter",
                        "outFields": "*",
                        "returnGeometry": "false",
                        "f": "json"
                    }
                    
                    response = requests.get(query_url, params=params, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("features"):
                            feature = data["features"][0]
                            attributes = feature["attributes"]
                            
                            overlays.append({
                                "overlay_type": overlay_name,
                                "description": attributes.get("descrip") or attributes.get("nombre", ""),
                                "source": "MIPR Reglamentario",
                                "code": attributes.get("codigo", ""),
                                "restrictions": attributes,
                                "last_updated": self._parse_date(attributes.get("fecha_actualizacion"))
                            })
                
                except Exception as e:
                    logger.warning(f"Error querying overlay {overlay_name}: {e}")
                    continue
            
            return overlays
            
        except Exception as e:
            logger.error(f"Error in get_overlay_zones: {e}")
            return []
    
    def get_municipal_pot(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict]:
        """
        Check if location is within a municipal POT (Plan de Ordenación Territorial)
        
        Returns:
            {
                "has_pot": True,
                "municipality": "San Juan",
                "pot_name": "POT San Juan 2015",
                "pot_district": "R-3",  # Municipal-specific code
                "equivalent_rc": "R-U",  # Reglamento Conjunto equivalent
                "requires_equivalency": True,
                "last_updated": "2023-06-15"
            }
        """
        
        try:
            # Query POT layer in Reglamentario service
            layer_id = self._get_layer_id(self.reglamentario_url, "pot")
            
            if layer_id is None:
                return {
                    "has_pot": False,
                    "error": "POT layer not found"
                }
            
            x, y = self._wgs84_to_web_mercator(longitude, latitude)
            
            query_url = f"{self.reglamentario_url}/{layer_id}/query"
            
            params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": "3857",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
            
            response = requests.get(query_url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return {"has_pot": False, "error": "Query failed"}
            
            data = response.json()
            
            if not data.get("features"):
                return {"has_pot": False}
            
            feature = data["features"][0]
            attributes = feature["attributes"]
            
            return {
                "has_pot": True,
                "municipality": attributes.get("municipio", ""),
                "pot_name": attributes.get("nombre_pot", ""),
                "pot_district": attributes.get("distrito", ""),
                "last_updated": self._parse_date(attributes.get("fecha_aprobacion")),
                "requires_equivalency": True,  # Always need to check equivalency table
                "raw_data": attributes
            }
            
        except Exception as e:
            logger.error(f"Error in get_municipal_pot: {e}")
            return {"has_pot": False, "error": str(e)}
    
    def get_parcel_info(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict]:
        """
        Get parcel/CRIM information at coordinate
        
        Returns:
            {
                "parcel_id": "123-456-789",
                "municipality": "San Juan",
                "barrio": "Santurce",
                "area_sqm": 500.5,
                "address": "Calle Luna 123"
            }
        """
        
        try:
            # Note: CRIM service might require different auth
            # This is a simplified implementation
            
            x, y = self._wgs84_to_web_mercator(longitude, latitude)
            
            # Try to find parcelas layer
            layer_id = 0  # Usually layer 0, but should be discovered
            
            query_url = f"{self.parcelas_url}/{layer_id}/query"
            
            params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": "3857",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
            
            response = requests.get(query_url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data.get("features"):
                return None
            
            feature = data["features"][0]
            attributes = feature["attributes"]
            
            return {
                "parcel_id": attributes.get("CRIM") or attributes.get("catastro"),
                "municipality": attributes.get("municipio", ""),
                "barrio": attributes.get("barrio", ""),
                "area_sqm": attributes.get("area", 0),
                "address": attributes.get("direccion", ""),
                "raw_data": attributes
            }
            
        except Exception as e:
            logger.warning(f"Could not retrieve parcel info: {e}")
            return None
    
    def get_complete_property_info(
        self,
        latitude: float,
        longitude: float
    ) -> Dict:
        """
        Get comprehensive property information including zoning, overlays, POT, and parcel
        
        This is the main method to use for validation
        """
        
        result = {
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "timestamp": datetime.now().isoformat(),
            "data_freshness_warning": "⚠️ MIPR database is actively being updated by agencies/municipalities. Verify critical data with local authorities.",
        }
        
        # Get zoning
        zoning = self.get_zoning_at_point(latitude, longitude)
        result["zoning"] = zoning
        
        # Get overlays
        overlays = self.get_overlay_zones(latitude, longitude)
        result["overlays"] = overlays
        
        # Check for municipal POT
        pot = self.get_municipal_pot(latitude, longitude)
        result["municipal_pot"] = pot
        
        # Get parcel info (optional)
        parcel = self.get_parcel_info(latitude, longitude)
        result["parcel"] = parcel
        
        # Determine which regulatory framework applies
        if pot and pot.get("has_pot"):
            result["regulatory_framework"] = "Municipal POT + Reglamento Conjunto (requires equivalency)"
            result["primary_regulation"] = pot["pot_name"]
        else:
            result["regulatory_framework"] = "Reglamento Conjunto 2023"
            result["primary_regulation"] = "Reglamento Conjunto"
        
        # Calculate overall confidence
        confidence_factors = []
        
        if zoning.get("confidence") == "high":
            confidence_factors.append("zoning_confirmed")
        
        if overlays:
            confidence_factors.append("overlays_identified")
        
        if pot and pot.get("has_pot"):
            confidence_factors.append("pot_applies")
        
        if parcel:
            confidence_factors.append("parcel_verified")
        
        result["data_confidence"] = {
            "level": "high" if len(confidence_factors) >= 2 else "medium",
            "factors": confidence_factors
        }
        
        return result
    
    # Helper methods
    
    def _get_layer_id(self, service_url: str, layer_name: str) -> Optional[int]:
        """Get layer ID by name from ArcGIS service"""
        
        # Check cache
        cache_key = f"{service_url}:{layer_name}"
        if cache_key in self._layer_cache:
            return self._layer_cache[cache_key]
        
        try:
            # Get service metadata
            response = requests.get(
                service_url,
                params={"f": "json"},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Search for layer by name
            for layer in data.get("layers", []):
                if layer_name.lower() in layer["name"].lower():
                    layer_id = layer["id"]
                    self._layer_cache[cache_key] = layer_id
                    return layer_id
            
            # Try tables too
            for table in data.get("tables", []):
                if layer_name.lower() in table["name"].lower():
                    table_id = table["id"]
                    self._layer_cache[cache_key] = table_id
                    return table_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting layer ID for {layer_name}: {e}")
            return None
    
    def _wgs84_to_web_mercator(self, lon: float, lat: float) -> Tuple[float, float]:
        """
        Convert WGS84 (EPSG:4326) to Web Mercator (EPSG:3857)
        
        Simple conversion for Puerto Rico region
        """
        import math
        
        x = lon * 20037508.34 / 180.0
        y = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        y = y * 20037508.34 / 180.0
        
        return x, y
    
    def _parse_date(self, date_value) -> Optional[str]:
        """Parse various date formats from ArcGIS"""
        
        if not date_value:
            return None
        
        # If already string, return
        if isinstance(date_value, str):
            return date_value
        
        # If timestamp (milliseconds since epoch)
        if isinstance(date_value, (int, float)):
            try:
                dt = datetime.fromtimestamp(date_value / 1000)
                return dt.strftime("%Y-%m-%d")
            except:
                return None
        
        return None
    
    def _error_response(self, error_message: str, confidence: str = "low") -> Dict:
        """Standard error response format"""
        return {
            "district_code": None,
            "district_name": None,
            "source": "MIPR",
            "last_updated": None,
            "confidence": confidence,
            "raw_data": {},
            "error": error_message
        }


# Example usage
if __name__ == "__main__":
    client = ArcGISPRClient()
    
    # Example: Old San Juan address
    lat, lon = 18.4655, -66.1057
    
    print("Getting property info...")
    info = client.get_complete_property_info(lat, lon)
    
    import json
    print(json.dumps(info, indent=2, ensure_ascii=False))