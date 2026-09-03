"""
ArcGIS PR Client - Integration with MIPR and CRIM GIS services
Ported from src/services/arcgis_pr_client.py
"""
import math
import httpx
from typing import Dict, Tuple


class ArcGISPRClient:
    """Client for Puerto Rico GIS services (MIPR and CRIM)"""

    CALIFICACION_URL = "https://sige.pr.gov/server/rest/services/MIPR/Calificacion/MapServer/0/query"
    REGLAMENTARIO_URL = "https://sige.pr.gov/server/rest/services/MIPR/Reglamentario/MapServer"
    CRIM_PARCELAS_URL = "https://sigejp.pr.gov/server/rest/services/crim/crim_parcelas/MapServer/0/query"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.client = httpx.Client(
            headers={
                "User-Agent": "Pyxten/1.0",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def _lat_lng_to_web_mercator(self, lat: float, lng: float) -> Tuple[float, float]:
        """Convert WGS84 (lat/lng) to Web Mercator (EPSG:3857)"""
        x = lng * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return (x, y)

    def get_zoning_district(self, lat: float, lng: float) -> Dict:
        """Query MIPR Calificación layer for zoning district at coordinates"""
        x, y = self._lat_lng_to_web_mercator(lat, lng)

        # Primary query: point-within-polygon (no buffer)
        params = {
            "geometry": f"{x},{y}",
            "geometryType": "esriGeometryPoint",
            "inSR": "3857",
            "spatialRel": "esriSpatialRelWithin",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }

        try:
            response = self.client.get(self.CALIFICACION_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return {
                    "success": False,
                    "district_code": None,
                    "district_name": None,
                    "error": data["error"].get("message", "Unknown API error"),
                }

            features = data.get("features", [])

            # How the match was obtained. A point-in-polygon hit is the parcel;
            # a buffer hit may be a NEIGHBOUR's parcel, and any caller making a
            # determination needs to be able to tell the difference.
            matched_by = "within"

            # Fallback: if no result with esriSpatialRelWithin, try intersects with 50m buffer
            # (handles points near polygon boundaries)
            if not features:
                fallback_params = {
                    "geometry": f"{x},{y}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": "3857",
                    "spatialRel": "esriSpatialRelIntersects",
                    "distance": 50,
                    "units": "esriSRUnit_Meter",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "f": "json",
                }
                fallback_response = self.client.get(self.CALIFICACION_URL, params=fallback_params)
                fallback_response.raise_for_status()
                fallback_data = fallback_response.json()
                features = fallback_data.get("features", [])
                if features:
                    matched_by = "buffer"
                # More than one polygon within 50 m means the point sits near a
                # boundary and the zoning cannot be attributed to one parcel.
                if len(features) > 1:
                    matched_by = "ambiguous"

            if not features:
                return {
                    "success": False,
                    "district_code": None,
                    "district_name": None,
                    "error": "No zoning data found at this location",
                }

            attrs = features[0].get("attributes", {})

            # Actual field names in MIPR/Calificacion MapServer layer 0:
            # cali = calificacion code, descrip = description
            district_code = (
                attrs.get("cali")
                or attrs.get("CALIFICACION")
                or attrs.get("Calificacion")
                or attrs.get("CODIGO")
                or attrs.get("COD_CALIF")
            )

            district_name = (
                attrs.get("descrip")
                or attrs.get("DESCRIPCION")
                or attrs.get("Descripcion")
                or attrs.get("DESC_CALIF")
            )

            return {
                "success": True,
                "district_code": district_code,
                "district_name": district_name,
                "matched_by": matched_by,
                "candidates": len(features),
                "error": None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "district_code": None,
                "district_name": None,
                "error": "Timeout connecting to MIPR Calificacion service",
            }
        except Exception as e:
            return {
                "success": False,
                "district_code": None,
                "district_name": None,
                "error": f"Connection error: {str(e)}",
            }

    def get_parcel_info(self, lat: float, lng: float) -> Dict:
        """Query CRIM parcels layer for catastro number at coordinates"""
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
            "f": "json",
        }

        try:
            response = self.client.get(self.CRIM_PARCELAS_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return {
                    "success": False,
                    "catastro": None,
                    "municipality": None,
                    "barrio": None,
                    "error": data["error"].get("message", "Unknown API error"),
                }

            features = data.get("features", [])

            if not features:
                return {
                    "success": False,
                    "catastro": None,
                    "municipality": None,
                    "barrio": None,
                    "error": "No parcel data found at this location",
                }

            attrs = features[0].get("attributes", {})

            catastro = (
                attrs.get("NUM_CATASTRO")
                or attrs.get("CATASTRO")
                or attrs.get("Catastro")
                or attrs.get("NUMERO")
                or attrs.get("NUM_CAT")
                or attrs.get("FINCA")
            )

            municipality = (
                attrs.get("MUNICIPIO") or attrs.get("Municipio") or attrs.get("MUN")
            )

            barrio = attrs.get("BARRIO") or attrs.get("Barrio")

            return {
                "success": True,
                "catastro": catastro,
                "municipality": municipality,
                "barrio": barrio,
                "raw_data": attrs,
                "error": None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "catastro": None,
                "municipality": None,
                "barrio": None,
                "error": "Timeout connecting to CRIM service",
            }
        except Exception as e:
            return {
                "success": False,
                "catastro": None,
                "municipality": None,
                "barrio": None,
                "error": f"Connection error: {str(e)}",
            }

    def get_overlay_zones(self, lat: float, lng: float) -> Dict:
        """Query overlay zones (historic, coastal, flood) at coordinates"""
        x, y = self._lat_lng_to_web_mercator(lat, lng)
        overlays_found = []
        errors = []

        # Query FEMA flood layer (known ID: 32)
        try:
            fema_result = self._query_overlay_layer(x, y, 32, "FEMA Flood Zone")
            if fema_result.get("found"):
                overlays_found.append(
                    {
                        "type": "area_inundacion",
                        "name": "FEMA Flood Zone",
                        "details": fema_result.get("attributes", {}),
                    }
                )
        except Exception as e:
            errors.append(f"FEMA query failed: {str(e)}")

        return {
            "success": len(errors) == 0,
            "overlays": overlays_found,
            "error": "; ".join(errors) if errors else None,
        }

    def _query_overlay_layer(
        self, x: float, y: float, layer_id: int, layer_name: str
    ) -> Dict:
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
            "f": "json",
        }

        response = self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        features = data.get("features", [])

        if features:
            return {"found": True, "attributes": features[0].get("attributes", {})}

        return {"found": False, "attributes": {}}

