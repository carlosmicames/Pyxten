
Copy

"""
ArcGIS PR Client - Integration with MIPR and CRIM GIS services
Queries zoning (Calificación), parcels (CRIM), and overlay zones
"""

import requests
import math
from typing import Dict, Optional, Tuple
import os

class ArcGISPRClient:
    """Client for Puerto Rico GIS services (MIPR and CRIM)"""
    
    # Service endpoints
    CALIFICACION_URL = "https://sige.pr.gov/server/rest/services/MIPR/Calificacion/MapServer/0/query"
    REGLAMENTARIO_URL = "https://sige.pr.gov/server/rest/services/MIPR/Reglamentario/MapServer"
    CRIM_PARCELAS_URL = "https://sigejp.pr.gov/server/rest/services/crim/crim_parcelas/MapServer/0/query"
    
    # Known overlay layer IDs in Reglamentario MapServer
    OVERLAY_LAYERS = {
        "zona_historica": None,  # Will be discovered dynamically
        "zona_costanera": None,
        "area_inundacion": None,
        "fema": 32  # Known layer ID for FEMA flood maps
    }
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Pyxten/1.0',
            'Accept': 'application/json'
        })
    
    def _lat_lng_to_web_mercator(self, lat: float, lng: float) -> Tuple[float, float]:
        """Convert WGS84 (lat/lng) to Web Mercator (EPSG:3857)"""
        x = lng * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return (x, y)
    
    def get_zoning_district(self, lat: float, lng: float) -> Dict:
        """
        Query MIPR Calificación layer for zoning district at coordinates
        
        Args:
            lat: Latitude (WGS84)
            lng: Longitude (WGS84)
        
        Returns:
            {
                "success": bool,
                "district_code": str or None,
                "district_name": str or None,
                "source": str,
                "raw_data": dict,
                "error": str or None
            }
        """
        x, y = self._lat_lng_to_web_mercator(lat, lng)
        
        params = {
            "geometry": f"{x},{y}",
            "geometryType": "esriGeometryPoint",
            "inSR": "3857",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": 10,
            "units": "esriSRUnit_Meter",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json"
        }
        
        try:
            response = self.session.get(
                self.CALIFICACION_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                return {
                    "success": False,
                    "district_code": None,
                    "district_name": None,
                    "source": "MIPR Calificacion",
                    "raw_data": data,
                    "error": data["error"].get("message", "Unknown API error")
                }
            
            features = data.get("features", [])
            
            if not features:
                return {
                    "success": False,
                    "district_code": None,
                    "district_name": None,
                    "source": "MIPR Calificacion",
                    "raw_data": data,
                    "error": "No zoning data found at this location"
                }
            
            # Extract attributes from first feature
            attrs = features[0].get("attributes", {})
            
            # Common field names in MIPR Calificación layer
            district_code = (
                attrs.get("CALIFICACION") or 
                attrs.get("Calificacion") or
                attrs.get("DISTRITO") or
                attrs.get("Distrito") or
                attrs.get("CODIGO") or
                attrs.get("Codigo") or
                attrs.get("COD_CALIF")
            )
            
            district_name = (
                attrs.get("DESCRIPCION") or
                attrs.get("Descripcion") or
                attrs.get("NOMBRE") or
                attrs.get("Nombre") or
                attrs.get("DESC_CALIF")
            )
            
            return {
                "success": True,
                "district_code": district_code,
                "district_name": district_name,
                "source": "MIPR Calificacion",
                "raw_data": attrs,
                "error": None
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "district_code": None,
                "district_name": None,
                "source": "MIPR Calificacion",
                "raw_data": None,
                "error": "Timeout connecting to MIPR service"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "district_code": None,
                "district_name": None,
                "source": "MIPR Calificacion",
                "raw_data": None,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "district_code": None,
                "district_name": None,
                "source": "MIPR Calificacion",
                "raw_data": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_parcel_info(self, lat: float, lng: float) -> Dict:
        """
        Query CRIM parcels layer for catastro number at coordinates
        
        Args:
            lat: Latitude (WGS84)
            lng: Longitude (WGS84)
        
        Returns:
            {
                "success": bool,
                "catastro": str or None,
                "municipality": str or None,
                "barrio": str or None,
                "raw_data": dict,
                "error": str or None
            }
        """
        x, y = self._lat_lng_to_web_mercator(lat, lng)
        
        params = {
            "geometry": f"{x},{y}",
            "geometryType": "esriGeometryPoint",
            "inSR": "3857",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": 10,
            "units": "esriSRUnit_Meter",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json"
        }
        
        try:
            response = self.session.get(
                self.CRIM_PARCELAS_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                return {
                    "success": False,
                    "catastro": None,
                    "municipality": None,
                    "barrio": None,
                    "raw_data": data,
                    "error": data["error"].get("message", "Unknown API error")
                }
            
            features = data.get("features", [])
            
            if not features:
                return {
                    "success": False,
                    "catastro": None,
                    "municipality": None,
                    "barrio": None,
                    "raw_data": data,
                    "error": "No parcel data found at this location"
                }
            
            attrs = features[0].get("attributes", {})
            
            # Common field names in CRIM parcels layer
            catastro = (
                attrs.get("NUM_CATASTRO") or
                attrs.get("CATASTRO") or
                attrs.get("Catastro") or
                attrs.get("NUMERO") or
                attrs.get("NUM_CAT") or
                attrs.get("FINCA")
            )
            
            municipality = (
                attrs.get("MUNICIPIO") or
                attrs.get("Municipio") or
                attrs.get("MUN")
            )
            
            barrio = (
                attrs.get("BARRIO") or
                attrs.get("Barrio")
            )
            
            return {
                "success": True,
                "catastro": catastro,
                "municipality": municipality,
                "barrio": barrio,
                "raw_data": attrs,
                "error": None
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "catastro": None,
                "municipality": None,
                "barrio": None,
                "raw_data": None,
                "error": "Timeout connecting to CRIM service"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "catastro": None,
                "municipality": None,
                "barrio": None,
                "raw_data": None,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "catastro": None,
                "municipality": None,
                "barrio": None,
                "raw_data": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_overlay_zones(self, lat: float, lng: float) -> Dict:
        """
        Query overlay zones (historic, coastal, flood) at coordinates
        
        Returns:
            {
                "success": bool,
                "overlays": [
                    {"type": "zona_historica", "name": "...", "details": {...}},
                    ...
                ],
                "error": str or None
            }
        """
        x, y = self._lat_lng_to_web_mercator(lat, lng)
        overlays_found = []
        errors = []
        
        # Query FEMA flood layer (known ID: 32)
        try:
            fema_result = self._query_overlay_layer(x, y, 32, "FEMA Flood Zone")
            if fema_result.get("found"):
                overlays_found.append({
                    "type": "area_inundacion",
                    "name": "FEMA Flood Zone",
                    "details": fema_result.get("attributes", {})
                })
        except Exception as e:
            errors.append(f"FEMA query failed: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "overlays": overlays_found,
            "error": "; ".join(errors) if errors else None
        }
    
    def _query_overlay_layer(self, x: float, y: float, layer_id: int, layer_name: str) -> Dict:
        """Query a specific overlay layer"""
        url = f"{self.REGLAMENTARIO_URL}/{layer_id}/query"
        
        params = {
            "geometry": f"{x},{y}",
            "geometryType": "esriGeometryPoint",
            "inSR": "3857",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": 10,
            "units": "esriSRUnit_Meter",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json"
        }
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        
        features = data.get("features", [])
        
        if features:
            return {
                "found": True,
                "attributes": features[0].get("attributes", {})
            }
        
        return {"found": False, "attributes": {}}
    
    def validate_location(self, lat: float, lng: float) -> Dict:
        """
        Complete location validation - gets zoning, catastro, and overlays
        
        Returns combined result with all available data
        """
        result = {
            "success": False,
            "zoning": None,
            "catastro": None,
            "overlays": [],
            "warnings": [],
            "errors": []
        }
        
        # Get zoning district
        zoning_result = self.get_zoning_district(lat, lng)
        if zoning_result["success"]:
            result["zoning"] = {
                "code": zoning_result["district_code"],
                "name": zoning_result["district_name"],
                "source": zoning_result["source"]
            }
        else:
            result["warnings"].append(f"Zoning lookup failed: {zoning_result['error']}")
        
        # Get parcel/catastro info
        parcel_result = self.get_parcel_info(lat, lng)
        if parcel_result["success"]:
            result["catastro"] = {
                "number": parcel_result["catastro"],
                "municipality": parcel_result["municipality"],
                "barrio": parcel_result["barrio"]
            }
        else:
            result["warnings"].append(f"Catastro lookup failed: {parcel_result['error']}")
        
        # Get overlay zones
        overlay_result = self.get_overlay_zones(lat, lng)
        result["overlays"] = overlay_result.get("overlays", [])
        if overlay_result.get("error"):
            result["warnings"].append(f"Overlay lookup partial: {overlay_result['error']}")
        
        # Consider success if we got at least zoning OR catastro
        result["success"] = (result["zoning"] is not None or result["catastro"] is not None)
        
        return result