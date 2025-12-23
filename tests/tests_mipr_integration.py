"""
Quick Test Script for MIPR Integration
Tests ArcGIS PR Client with known coordinates
"""

import sys
from pathlib import Path
import json

# Add project root to Python path so "src.*" imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.arcgis_pr_client import ArcGISPRClient
from src.utils.pot_equivalency import POTEquivalencyTable


def test_mipr_integration():
    print("=" * 80)
    print("TESTING MIPR INTEGRATION")
    print("=" * 80)

    client = ArcGISPRClient()
    pot_table = POTEquivalencyTable()

    test_cases = [
        {
            "name": "Old San Juan - Calle del Cristo",
            "lat": 18.4655,
            "lon": -66.1166,
            "expected_zone": "S-H or C-H (Historic)",
            "expected_overlays": ["Zona Histórica"],
        },
        {
            "name": "Condado - Av. Ashford",
            "lat": 18.4611,
            "lon": -66.0749,
            "expected_zone": "C-T or RT (Tourist)",
            "expected_overlays": ["Zona Costanera"],
        },
        {
            "name": "Santurce - Residential Area",
            "lat": 18.4500,
            "lon": -66.0500,
            "expected_zone": "R-U, R-I, or R-B (Residential)",
            "expected_overlays": [],
        },
        {
            "name": "Ponce Centro",
            "lat": 18.0111,
            "lon": -66.6141,
            "expected_zone": "C-L, C-I, or C-H (Commercial/Historic)",
            "expected_overlays": [],
        },
        {
            "name": "Carolina - Near Airport",
            "lat": 18.4247,
            "lon": -65.9989,
            "expected_zone": "I-L, C-I, or C-C (Industrial/Commercial)",
            "expected_overlays": [],
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'=' * 80}")
        print(f"Coordinates: {test['lat']}, {test['lon']}")
        print(f"Expected Zone: {test['expected_zone']}")
        print(
            f"Expected Overlays: {', '.join(test['expected_overlays']) if test['expected_overlays'] else 'None'}"
        )
        print()

        try:
            info = client.get_complete_property_info(test["lat"], test["lon"])

            zoning = info.get("zoning", {})
            overlays = info.get("overlays", [])
            pot = info.get("municipal_pot", {})

            print("RESULTS:")
            print(f"  District Code: {zoning.get('district_code', 'NOT FOUND')}")
            print(f"  District Name: {zoning.get('district_name', 'NOT FOUND')}")
            print(f"  Source: {zoning.get('source', 'N/A')}")
            print(f"  Last Updated: {zoning.get('last_updated', 'N/A')}")
            print(f"  Confidence: {zoning.get('confidence', 'N/A')}")

            if zoning.get("error"):
                print(f"  ⚠️ ERROR: {zoning['error']}")

            if zoning.get("district_code"):
                if pot_table.is_municipal_specific(zoning["district_code"]):
                    equiv = pot_table.get_rc_equivalent(zoning["district_code"], "2020")
                    if equiv:
                        print("\n  POT Equivalency:")
                        print(f"    Municipal Code: {zoning['district_code']}")
                        print(f"    RC 2020: {equiv['rc_code']} ({equiv['rc_name']})")
                else:
                    print(f"\n  Already using RC 2020 codes: {zoning['district_code']}")

            print(f"\n  Overlays Detected: {len(overlays)}")
            for overlay in overlays:
                print(f"    - {overlay.get('overlay_type', 'UNKNOWN')}: {overlay.get('description', 'N/A')}")

            results.append(
                {
                    "test_name": test["name"],
                    "success": not zoning.get("error"),
                    "zoning": zoning,
                    "overlays": overlays,
                    "pot": pot,
                }
            )

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({"test_name": test["name"], "success": False, "error": str(e)})

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"\nTests Passed: {successful}/{total} ({successful/total*100:.1f}%)\n")

    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test_name']}")
        if result["success"] and result.get("zoning", {}).get("district_code"):
            z = result["zoning"]
            print(f"   → {z['district_code']} - {z.get('district_name', '')}")

    # Save detailed results
    output_dir = PROJECT_ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "mipr_test_results.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Detailed results saved to: {output_file}\n")


if __name__ == "__main__":
    test_mipr_integration()