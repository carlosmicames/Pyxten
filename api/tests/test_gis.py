"""
The GIS wrapper.

The applicant flow catches every GIS error and returns success with no overlays,
so a timeout there is indistinguishable from a clean parcel. These tests exist
to prove that cannot happen on the reviewer path: every failure mode produces a
quality flag that makes the zoning rule escalate.
"""
import pytest

from app.reviewer import gis
from app.reviewer.gis import AMBIGUOUS, NO_RESULT, OFFLINE, OK, UNEXPECTED, SOURCE_ZONING


CASE = {
    "id": "case-1",
    "property_address": "Calle Loiza 500",
    "ruleset_version_id": "rs-1",
}


@pytest.fixture()
def wired(monkeypatch, reviewer_ctx):
    """
    Stub the three external services. Each test overrides only what it is about.
    """
    state = {
        "geocode": {"valid": True, "latitude": 18.45, "longitude": -66.05},
        "parcel": {"success": True, "catastro": "123-456-789-01"},
        "zoning": {
            "success": True,
            "district_code": "C-L",
            "district_name": "Comercial Liviano",
            "matched_by": "within",
        },
        "mappings": [{"use_code": "COM-RETAIL", "keywords": ["panaderia"]}],
        "activity": {
            "value_text": "Panaderia y reposteria",
            "source_page": 2,
            "document_id": "doc-pat",
            "band": "alta",
            "status": "extraido",
        },
    }

    class FakeAddress:
        def validate_address(self, address, municipality, country="Puerto Rico"):
            return state["geocode"]

    class FakeArcGIS:
        def get_parcel_info(self, lat, lng):
            return state["parcel"]

        def get_zoning_district(self, lat, lng):
            return state["zoning"]

    monkeypatch.setattr(gis, "AddressValidator", lambda: FakeAddress())
    monkeypatch.setattr(gis, "ArcGISPRClient", lambda: FakeArcGIS())
    monkeypatch.setattr(gis, "load_use_mappings", lambda ctx, ruleset_id: state["mappings"])

    original_select_one = reviewer_ctx.db.select_one

    def select_one(table, *, columns="*", filters=None):
        if table == "extracted_facts":
            return state["activity"]
        return original_select_one(table, columns=columns, filters=filters)

    reviewer_ctx.db.select_one = select_one
    return state, reviewer_ctx


def _zoning_row(ctx):
    rows = [
        r for r in ctx.db.rows("external_verifications") if r["source"] == SOURCE_ZONING
    ]
    assert rows, "no zoning verification was recorded"
    return rows[-1]


# =============================================================================
# Keyword mapping - deterministic, and it declines to guess
# =============================================================================

def test_activity_maps_to_a_use_code_by_keyword():
    mappings = [
        {"use_code": "COM-RETAIL", "keywords": ["panaderia", "colmado"]},
        {"use_code": "COM-RESTAURANT", "keywords": ["restaurante"]},
    ]
    assert gis.match_use_code("PANADERÍA Y REPOSTERÍA", mappings) == "COM-RETAIL"


def test_an_activity_matching_nothing_returns_none():
    assert gis.match_use_code("taller de reparacion de drones", [
        {"use_code": "COM-RETAIL", "keywords": ["panaderia"]},
    ]) is None


def test_an_ambiguous_activity_is_not_resolved_by_picking_one():
    """Two plausible codes is a reviewer's call, not a coin flip."""
    mappings = [
        {"use_code": "COM-RETAIL", "keywords": ["panaderia"]},
        {"use_code": "COM-RESTAURANT", "keywords": ["cafeteria"]},
    ]
    assert gis.match_use_code("Panaderia y cafeteria", mappings) is None


def test_empty_activity_returns_none():
    assert gis.match_use_code("", [{"use_code": "X", "keywords": ["y"]}]) is None


# =============================================================================
# The happy path
# =============================================================================

def test_compatible_use_records_a_matched_determination(wired):
    state, ctx = wired
    result = gis.run_lookups(ctx, "case-1", CASE)

    row = _zoning_row(ctx)
    assert result["resultado"] == "ok"
    assert row["quality_flag"] == OK
    assert row["matched"] is True
    assert row["response"]["codigo_uso"] == "COM-RETAIL"
    assert row["response"]["value"] == "C-L"
    # The raw response is kept so the determination survives a schema change.
    assert "zonas_compatibles" in row["response"]


def test_incompatible_use_records_an_unmatched_determination(wired):
    state, ctx = wired
    state["zoning"]["district_code"] = "R-B"   # residential; retail is not allowed

    gis.run_lookups(ctx, "case-1", CASE)
    row = _zoning_row(ctx)

    assert row["quality_flag"] == OK
    assert row["matched"] is False
    assert row["response"]["compatible"] is False


def test_the_parcel_lookup_is_recorded_as_evidence(wired):
    state, ctx = wired
    gis.run_lookups(ctx, "case-1", CASE)

    parcel = [r for r in ctx.db.rows("external_verifications") if r["source"] == "crim_parcelas"]
    assert parcel and parcel[0]["response"]["value"] == "123-456-789-01"


def test_every_run_is_audited(wired):
    state, ctx = wired
    gis.run_lookups(ctx, "case-1", CASE)
    assert "gis_lookup_run" in ctx.db.audit_types()


# =============================================================================
# Every failure mode escalates. None of them can pass.
# =============================================================================

def test_a_service_outage_never_reads_as_a_clean_parcel(wired):
    state, ctx = wired
    state["zoning"] = {"success": False, "error": "Timeout connecting to MIPR Calificacion service"}

    result = gis.run_lookups(ctx, "case-1", CASE)
    row = _zoning_row(ctx)

    assert result["resultado"] == "calificacion_no_disponible"
    assert row["quality_flag"] == OFFLINE
    assert row["matched"] is None


def test_a_buffer_hit_is_ambiguous_because_it_may_be_a_neighbour(wired):
    """
    The point fell outside every calificacion polygon and matched by proximity.
    That parcel may not be this parcel, so nothing is attributed to it.
    """
    state, ctx = wired
    state["zoning"]["matched_by"] = "buffer"

    result = gis.run_lookups(ctx, "case-1", CASE)
    row = _zoning_row(ctx)

    assert result["resultado"] == "calificacion_buffer"
    assert row["quality_flag"] == AMBIGUOUS
    assert row["matched"] is None
    assert "proximidad" in row["response"]["nota"]


def test_multiple_candidate_parcels_are_ambiguous(wired):
    state, ctx = wired
    state["zoning"]["matched_by"] = "ambiguous"

    gis.run_lookups(ctx, "case-1", CASE)
    assert _zoning_row(ctx)["quality_flag"] == AMBIGUOUS


def test_a_district_with_no_pot_equivalence_escalates(wired, monkeypatch):
    state, ctx = wired
    state["zoning"]["district_code"] = "ZZ-INVENTADO"

    monkeypatch.setattr(
        gis.POTEquivalencyTable, "is_municipal_specific", lambda self, code: True
    )
    monkeypatch.setattr(
        gis.POTEquivalencyTable, "get_rc_equivalent", lambda self, code, version: None
    )

    result = gis.run_lookups(ctx, "case-1", CASE)
    assert result["resultado"] == "equivalencia_pot_ausente"
    assert _zoning_row(ctx)["quality_flag"] == UNEXPECTED


def test_an_unreadable_activity_escalates(wired):
    state, ctx = wired
    state["activity"] = None

    result = gis.run_lookups(ctx, "case-1", CASE)
    assert result["resultado"] == "actividad_no_leida"
    assert _zoning_row(ctx)["quality_flag"] == NO_RESULT


def test_an_unmapped_activity_escalates_and_shows_what_was_declared(wired):
    state, ctx = wired
    state["activity"]["value_text"] = "servicios de dron para agricultura"

    result = gis.run_lookups(ctx, "case-1", CASE)
    row = _zoning_row(ctx)

    assert result["resultado"] == "uso_no_mapeado"
    assert row["quality_flag"] == AMBIGUOUS
    assert "servicios de dron" in row["response"]["nota"]


def test_a_failed_geocode_escalates(wired):
    state, ctx = wired
    state["geocode"] = {"valid": False, "error": "ZERO_RESULTS"}

    result = gis.run_lookups(ctx, "case-1", CASE)
    assert result["resultado"] == "geocodificacion_fallida"
    assert _zoning_row(ctx)["quality_flag"] == NO_RESULT


def test_a_case_with_no_address_escalates(wired):
    state, ctx = wired
    result = gis.run_lookups(ctx, "case-1", {**CASE, "property_address": ""})

    assert result["resultado"] == "direccion_ausente"
    assert _zoning_row(ctx)["quality_flag"] == NO_RESULT


def test_a_raising_client_is_caught_and_escalated(wired, monkeypatch):
    """A connection reset is a failure to find out, not a finding."""
    state, ctx = wired

    class Exploding:
        def get_parcel_info(self, lat, lng):
            raise RuntimeError("connection reset")

        def get_zoning_district(self, lat, lng):
            raise RuntimeError("connection reset")

    # monkeypatch, not a bare assignment: a direct write would outlive this test
    # and silently break whatever ran after it.
    monkeypatch.setattr(gis, "ArcGISPRClient", lambda: Exploding())

    result = gis.run_lookups(ctx, "case-1", CASE)

    assert result["resultado"] == "calificacion_no_disponible"
    assert _zoning_row(ctx)["matched"] is None


@pytest.mark.parametrize(
    "flag", [OK, NO_RESULT, AMBIGUOUS, OFFLINE, UNEXPECTED]
)
def test_quality_flags_match_the_database_constraint(flag):
    """
    These five are the CHECK constraint in migration 006. A sixth invented here
    would be rejected at insert time.
    """
    migration = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "migrations" / "006_rules_engine.sql"
    ).read_text(encoding="utf-8")
    assert f"'{flag}'" in migration
