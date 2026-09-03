"""
Zoning compatibility, as a recorded external determination.

WHAT THIS REUSES AND WHAT IT REPLACES
The regulatory logic is the applicant flow's, unchanged: ArcGISPRClient for the
MIPR and CRIM lookups, POTEquivalencyTable for the municipal-to-RC mapping, and
the use catalogue's `compatible_zones`. What it does NOT reuse is
Phase1ValidationService itself, for three reasons:

  * it constructs UseClassifier, which is an OpenAI client, and the reviewer
    path is Anthropic-only;
  * it synthesises a numeric confidence;
  * it catches every GIS error and returns success with no overlays, so a
    timeout is indistinguishable from a clean parcel.

The third is the one that matters most here. On this path an unreachable
service, an ambiguous parcel, an unmapped district or an unrecognised activity
all produce a quality flag that makes the rule escalate. There is no code path
from "we could not find out" to "compliant".

HOW THE PROPOSED USE IS DETERMINED
Not by a model. The activity is read off the applicant's own filed patente as an
extracted fact with a page citation, then matched against keyword mappings
stored as data alongside the ruleset. An activity that matches nothing escalates
to a reviewer rather than being guessed at.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.reviewer import audit
from app.reviewer.context import ReviewerContext
from app.reviewer.rules.normalize import basic
from app.services.arcgis_client import ArcGISPRClient
from app.services.address_validator import AddressValidator
from app.services.pot_equivalency import POTEquivalencyTable
from app.services.rules_data import get_rules_db

logger = logging.getLogger(__name__)

GIS_RUN = "gis_lookup_run"

# Sources recorded in external_verifications.
SOURCE_ZONING = "zonificacion"
SOURCE_PARCEL = "crim_parcelas"

# quality_flag values, matching the CHECK constraint in migration 006.
OK = "ok"
NO_RESULT = "sin_resultado"
AMBIGUOUS = "ambiguo"
OFFLINE = "fuera_de_servicio"
UNEXPECTED = "esquema_inesperado"


@dataclass
class Verification:
    source: str
    query: Dict[str, Any]
    response: Dict[str, Any]
    matched: Optional[bool]
    quality_flag: str

    def as_row(self, case_id: str, org_id: str) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "org_id": org_id,
            "source": self.source,
            "query": self.query,
            "response": self.response,
            "matched": self.matched,
            "quality_flag": self.quality_flag,
        }


# =============================================================================
# Use mapping - data, not a model
# =============================================================================

def load_use_mappings(ctx: ReviewerContext, ruleset_id: str) -> List[Dict[str, Any]]:
    try:
        return ctx.db.select(
            "use_mappings",
            columns="use_code,keywords",
            filters={"ruleset_id": f"eq.{ruleset_id}"},
        )
    except Exception as exc:
        logger.warning("Could not load use mappings: %s", exc)
        return []


def match_use_code(activity: str, mappings: List[Dict[str, Any]]) -> Optional[str]:
    """
    Map a declared activity to an RC use code by keyword.

    Deterministic and auditable: a municipality can see and edit exactly why
    "panaderia" resolved to COM-RETAIL. An activity matching more than one code,
    or none, returns None and the caller escalates - it does not pick a winner.
    """
    haystack = basic(activity)
    if not haystack:
        return None

    hits = {
        row["use_code"]
        for row in mappings
        for keyword in (row.get("keywords") or [])
        if keyword and basic(keyword) in haystack
    }

    return hits.pop() if len(hits) == 1 else None


# =============================================================================
# The lookup
# =============================================================================

def run_lookups(
    ctx: ReviewerContext,
    case_id: str,
    case: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Geocode the property, read the parcel and the calificacion, and record a
    zoning-compatibility determination.

    Every outcome is written to external_verifications with its raw response, so
    a determination stays reproducible after the commonwealth renames a field.
    """
    address = (case.get("property_address") or "").strip()
    municipality = ctx.municipality or ""

    verifications: List[Verification] = []

    if not address:
        verifications.append(
            Verification(
                SOURCE_ZONING,
                {"motivo": "direccion_ausente"},
                {},
                None,
                NO_RESULT,
            )
        )
        return _persist(ctx, case_id, verifications, note="direccion_ausente")

    # --- Geocode --------------------------------------------------------------
    try:
        geocode = AddressValidator().validate_address(address, municipality)
    except Exception as exc:
        logger.warning("Geocoding failed: %s", exc)
        geocode = {"valid": False, "error": str(exc)}

    if not geocode.get("valid"):
        verifications.append(
            Verification(
                SOURCE_ZONING,
                {"direccion": address, "municipio": municipality},
                {"error": geocode.get("error")},
                None,
                NO_RESULT,
            )
        )
        return _persist(ctx, case_id, verifications, note="geocodificacion_fallida")

    lat = geocode.get("latitude")
    lng = geocode.get("longitude")
    query = {"direccion": address, "municipio": municipality, "lat": lat, "lng": lng}

    client = ArcGISPRClient()

    # --- Parcel (evidence; also lets a reviewer compare the filed catastro) ---
    try:
        parcel = client.get_parcel_info(lat, lng)
    except Exception as exc:
        parcel = {"success": False, "error": str(exc)}

    verifications.append(
        Verification(
            SOURCE_PARCEL,
            query,
            {**parcel, "value": parcel.get("catastro")},
            bool(parcel.get("success") and parcel.get("catastro")),
            OK if parcel.get("success") and parcel.get("catastro") else NO_RESULT,
        )
    )

    # --- Calificacion ---------------------------------------------------------
    try:
        zoning = client.get_zoning_district(lat, lng)
    except Exception as exc:
        logger.warning("Zoning lookup raised: %s", exc)
        zoning = {"success": False, "error": str(exc)}

    if not zoning.get("success"):
        # An unreachable or empty service escalates. It never reads as a pass.
        flag = OFFLINE if "imeout" in str(zoning.get("error") or "") else NO_RESULT
        verifications.append(
            Verification(SOURCE_ZONING, query, zoning, None, flag)
        )
        return _persist(ctx, case_id, verifications, note="calificacion_no_disponible")

    # A buffer hit may be a neighbouring parcel. Never silently attribute it.
    matched_by = zoning.get("matched_by", "within")
    if matched_by != "within":
        verifications.append(
            Verification(
                SOURCE_ZONING,
                query,
                {
                    **zoning,
                    "value": zoning.get("district_code"),
                    "nota": (
                        "El punto no cae dentro de un poligono de calificacion; "
                        f"coincidencia por proximidad ({matched_by}). "
                        "Confirme la parcela manualmente."
                    ),
                },
                None,
                AMBIGUOUS,
            )
        )
        return _persist(ctx, case_id, verifications, note=f"calificacion_{matched_by}")

    district_code = (zoning.get("district_code") or "").strip().upper()
    if not district_code:
        verifications.append(
            Verification(SOURCE_ZONING, query, zoning, None, UNEXPECTED)
        )
        return _persist(ctx, case_id, verifications, note="calificacion_sin_codigo")

    # --- POT -> RC ------------------------------------------------------------
    pot = POTEquivalencyTable()
    rc_code = district_code
    equivalence = None

    if pot.is_municipal_specific(district_code):
        equivalence = pot.get_rc_equivalent(district_code, "2020")
        if not equivalence:
            verifications.append(
                Verification(
                    SOURCE_ZONING,
                    query,
                    {
                        **zoning,
                        "value": district_code,
                        "nota": (
                            f"El distrito municipal '{district_code}' no tiene "
                            "equivalencia registrada en la Tabla 6.1."
                        ),
                    },
                    None,
                    UNEXPECTED,
                )
            )
            return _persist(ctx, case_id, verifications, note="equivalencia_pot_ausente")
        rc_code = equivalence["rc_code"]

    # --- The declared activity, from the applicant's own document -------------
    activity_fact = ctx.db.select_one(
        "extracted_facts",
        columns="value_text,source_page,document_id,band,status",
        filters={
            "case_id": f"eq.{case_id}",
            "field_key": "eq.patente_municipal.actividad",
            "status": "eq.extraido",
        },
    )

    if not activity_fact or not activity_fact.get("value_text"):
        verifications.append(
            Verification(
                SOURCE_ZONING,
                query,
                {
                    **zoning,
                    "value": rc_code,
                    "nota": (
                        "No se pudo leer la actividad declarada en la patente, "
                        "por lo que no hay uso propuesto que comparar."
                    ),
                },
                None,
                NO_RESULT,
            )
        )
        return _persist(ctx, case_id, verifications, note="actividad_no_leida")

    activity = activity_fact["value_text"]
    mappings = load_use_mappings(ctx, case.get("ruleset_version_id"))
    use_code = match_use_code(activity, mappings)

    if not use_code:
        verifications.append(
            Verification(
                SOURCE_ZONING,
                query,
                {
                    **zoning,
                    "value": rc_code,
                    "actividad": activity,
                    "nota": (
                        f"La actividad declarada ('{activity}') no corresponde de "
                        "forma inequivoca a un uso del catalogo. Clasifiquela manualmente."
                    ),
                },
                None,
                AMBIGUOUS,
            )
        )
        return _persist(ctx, case_id, verifications, note="uso_no_mapeado")

    # --- Compatibility --------------------------------------------------------
    use_type = get_rules_db().get_use_type(use_code)
    compatible = list((use_type or {}).get("compatible_zones") or [])
    is_compatible = rc_code in compatible

    verifications.append(
        Verification(
            SOURCE_ZONING,
            {**query, "uso_declarado": activity, "codigo_uso": use_code},
            {
                "value": rc_code,
                "calificacion": district_code,
                "calificacion_descripcion": zoning.get("district_name"),
                "equivalencia_rc": equivalence,
                "codigo_uso": use_code,
                "uso_nombre": (use_type or {}).get("name_es"),
                "zonas_compatibles": compatible,
                "compatible": is_compatible,
                "matched_by": matched_by,
            },
            is_compatible,
            OK,
        )
    )

    return _persist(ctx, case_id, verifications, note="ok")


def _persist(
    ctx: ReviewerContext,
    case_id: str,
    verifications: List[Verification],
    note: str,
) -> Dict[str, Any]:
    rows = [v.as_row(case_id, ctx.org_id) for v in verifications]
    if rows:
        try:
            ctx.db.insert("external_verifications", rows, returning=False)
        except Exception as exc:
            logger.error("Could not store external verifications: %s", exc)

    audit.record(
        ctx,
        GIS_RUN,
        case_id=case_id,
        object_ref=case_id,
        payload={
            "resultado": note,
            "consultas": [
                {"source": v.source, "quality_flag": v.quality_flag, "matched": v.matched}
                for v in verifications
            ],
        },
    )

    return {
        "resultado": note,
        "consultas": [
            {
                "source": v.source,
                "quality_flag": v.quality_flag,
                "matched": v.matched,
                "nota": v.response.get("nota"),
                "valor": v.response.get("value"),
            }
            for v in verifications
        ],
    }
