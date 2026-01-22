"""
Address validation endpoint
Validates address using Google Geocoding and fetches catastro/overlays from ArcGIS
"""
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas import (
    AddressValidationRequest,
    AddressValidationResponse,
    UserInfo,
)
from app.services.address_validator import AddressValidator
from app.services.arcgis_client import ArcGISPRClient

router = APIRouter(tags=["address"])


@router.post("/validate-address", response_model=AddressValidationResponse)
def validate_address(
    request: AddressValidationRequest,
    user: UserInfo = Depends(get_current_user),
):
    """
    Validate an address and return coordinates, catastro number, and overlays.

    This endpoint:
    1. Geocodes the address using Google Maps API
    2. Fetches parcel/catastro info from ArcGIS CRIM
    3. Fetches overlay zones (flood, historic, coastal) from ArcGIS

    Note: This does NOT return zoning district - the user must manually select
    the district/calificacion from the dropdown.
    """
    address_validator = AddressValidator()
    arcgis_client = ArcGISPRClient()

    # Step 1: Geocode address
    geocode_result = address_validator.validate_address(
        request.address,
        request.municipality
    )

    if not geocode_result.get("valid"):
        return AddressValidationResponse(
            valid=False,
            error=geocode_result.get("error", "No se pudo validar la direccion"),
            formatted_address=geocode_result.get("formatted_address"),
        )

    lat = geocode_result["latitude"]
    lng = geocode_result["longitude"]

    # Step 2: Get parcel/catastro info from ArcGIS
    parcel_result = arcgis_client.get_parcel_info(lat, lng)
    catastro_number = None
    municipality_from_parcel = None

    if parcel_result.get("success"):
        catastro_number = parcel_result.get("catastro")
        municipality_from_parcel = parcel_result.get("municipality")

    # Step 3: Get overlay zones
    overlay_result = arcgis_client.get_overlay_zones(lat, lng)
    overlays = overlay_result.get("overlays", [])

    return AddressValidationResponse(
        valid=True,
        latitude=lat,
        longitude=lng,
        formatted_address=geocode_result.get("formatted_address"),
        catastro_number=catastro_number,
        municipality=municipality_from_parcel or request.municipality,
        overlays=overlays,
        gis_map_url="https://gis.jp.pr.gov/mipr/",
        disclaimer="Debe verificar esta informacion en el mapa oficial para confirmar su exactitud antes de continuar.",
    )
