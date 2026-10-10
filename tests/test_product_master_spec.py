import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_master_alert_catalog_has_exactly_97_configurable_alert_types():
    catalog = json.loads((ROOT / "docs/COALICION_ALERT_CATALOG.json").read_text(encoding="utf-8"))
    assert catalog["schema"] == "COALICION_ALERT_CATALOG_V1"
    assert catalog["expected_count"] == catalog["count"] == 97
    assert len(catalog["alerts"]) == 97
    assert len({item["id"] for item in catalog["alerts"]}) == 97
    assert [item["count"] for item in catalog["categories"]] == [15, 14, 14, 10, 12, 10, 10, 12]
    assert all(item["trigger_requires_evidence"] for item in catalog["alerts"])
    assert all(item["configurable"] for item in catalog["alerts"])


def test_traceability_matrix_separates_capability_monitoring_and_verification():
    matrix = json.loads((ROOT / "docs/COALICION_REQUIREMENT_TRACEABILITY.json").read_text(encoding="utf-8"))
    assert matrix["schema"] == "COALICION_REQUIREMENT_TRACEABILITY_V1"
    assert matrix["summary"]["capability_requirements"] == 142
    assert matrix["summary"]["monitoring_alert_types"] == 97
    assert matrix["summary"]["total"] == 239
    ids = [item["id"] for item in matrix["requirements"]]
    assert len(ids) == len(set(ids)) == 239
    assert all(item["requirement"] for item in matrix["requirements"])
    assert all(item["monitoring_requirement"] for item in matrix["requirements"])
    assert all(item["verification_requirement"] for item in matrix["requirements"])
    assert all(item["status"] == "NO VERIFICADO" for item in matrix["requirements"])
    assert all(not item["repository_evidence"] and not item["test_evidence"] for item in matrix["requirements"])


def test_master_spec_pins_official_election_dates_and_does_not_claim_runtime():
    spec = (ROOT / "docs/COALICION_MASTER_REQUIREMENTS.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs/COALICION_FIRST_PASS_AUDIT.md").read_text(encoding="utf-8")
    assert "29 de noviembre de 2026" in spec
    assert "13 al 27 de noviembre de 2026" in spec
    assert "BOE-A-2026-20742" in spec
    assert "no demuestra que el calendario ya esté implementado" in audit
    assert "ninguna fila se considera operativa" in audit.lower()
