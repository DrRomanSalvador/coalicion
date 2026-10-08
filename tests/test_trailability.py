from src.trailability.evidence import EvidenceBlocked, build_record, validate_records


def test_primary_evidence_requires_complete_traceability():
    record = build_record({
        "source_id": "sigma_dos",
        "primary_url": "https://www.sigmados.com/barometro-de-octubre-estimacion-de-voto-para-las-elecciones-generales/",
        "publication_date": "2026-10-05",
        "fieldwork_start": "2026-09-22",
        "fieldwork_end": "2026-10-01",
        "sample_size": 2116,
        "methodology": "CATI+CAWI",
        "source_tier": "PRIMARY_OFFICIAL",
        "validation": "PRIMARY_VERIFIED",
    }, content_sha256="0" * 64)
    assert validate_records([record], require_primary=True)["status"] == "PASS"


def test_missing_primary_url_fails_closed():
    try:
        build_record({"source_id": "x", "publication_date": "2026-10-08", "source_tier": "PRIMARY_OFFICIAL", "validation": "PRIMARY_VERIFIED"}, content_sha256="0" * 64)
    except EvidenceBlocked:
        return
    raise AssertionError("missing evidence was accepted")
