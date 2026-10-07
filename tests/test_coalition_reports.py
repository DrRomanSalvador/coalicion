import json
from pathlib import Path
import pytest
from src.coalition_reports import aggregate_identities, party_identity, pairwise_report

def test_identity_aliases_are_closed_and_not_fuzzy():
    assert party_identity("PP PARTIDO POPULAR") == "PP"
    assert party_identity("PSC PARTIT DELS SOCIALISTES DE CATALUNYA (PSC-PSOE)") == "PSOE"
    assert party_identity("PSE-EE (PSOE) PARTIDO SOCIALISTA DE EUSKADI-EUSKADIKO EZKERRA (PSOE)") == "PSOE"
    assert party_identity("SUMAR SUMAR") == "SUMAR"
    assert party_identity("ECP SUMAR - EN COMÚ PODEM - SUMAR") == "SUMAR"
    assert party_identity("COMPROMÍS COMPROMÍS - SUMAR: SUMEM PER GUANYAR - SUMAR") == "SUMAR"

def test_aggregate_preserves_votes_and_does_not_split_joint_candidacies():
    raw = {"Valencia": {
        "PP PARTIDO POPULAR": 100,
        "PSOE PARTIDO SOCIALISTA OBRERO ESPAÑOL": 80,
        "COMPROMÍS COMPROMÍS - SUMAR: SUMEM PER GUANYAR - SUMAR": 50,
    }}
    out = aggregate_identities(raw)["Valencia"]
    assert out["PP"] == 100
    assert out["PSOE"] == 80
    assert out["SUMAR"] == 50
    assert sum(out.values()) == 230

def test_real_matrix_reports_when_available():
    path = Path("artifacts/data/election_2023_canonical.json")
    if not path.exists():
        pytest.skip("matriz 2023 no materializada en este checkout")
    matrix = json.loads(path.read_text(encoding="utf-8"))
    results, unsupported = pairwise_report(matrix)
    assert len(results) == 78
    assert {"IU", "Podemos", "Más País", "Compromís"}.issubset(set(unsupported))
    sumar_psoe = next(r for r in results if {r["party_a"], r["party_b"]} == {"SUMAR", "PSOE"})
    pp_vox = next(r for r in results if {r["party_a"], r["party_b"]} == {"PP", "VOX"})
    assert (sumar_psoe["separate_seats"], sumar_psoe["coalition_seats"], sumar_psoe["delta"]) == (152, 172, 20)
    assert (pp_vox["separate_seats"], pp_vox["coalition_seats"], pp_vox["delta"]) == (170, 180, 10)
