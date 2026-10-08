from src.political_intelligence import (
    build_evidence_graph,
    evidence_requirements,
    validate_registry,
)


def test_registry_is_canonical_and_fail_closed():
    result = validate_registry()
    assert result["status"] == "PASS"
    assert result["canonical_general_elections"] == 16


def test_false_2023_november_election_is_not_canonical():
    result = validate_registry()
    assert result["canonical_general_elections"] == 16


def test_requirements_are_explicit():
    req = evidence_requirements()
    assert req["official_2023_candidacy_matrix"]["required"] is True
    assert req["historical_results"]["required_elections"] == 16
    assert req["survey_evidence"]["field_date_required_for_oos"] is True


def test_evidence_graph_is_deterministic():
    a = build_evidence_graph(as_of="2026-10-08")
    b = build_evidence_graph(as_of="2026-10-08")
    assert a["hash"] == b["hash"]
    assert a["policy"]["fail_closed"] is True
