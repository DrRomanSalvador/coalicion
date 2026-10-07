from pathlib import Path
from src.reproducibility_contract import ANCHOR_SHA256, ANCHOR_MANIFEST, verify_contract

def test_reproducibility_contract_is_fail_closed():
    result = verify_contract(Path("."))
    anchor_path = Path(ANCHOR_MANIFEST)
    binary_path = Path("data/source_anchors") / "INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.pdf"
    if anchor_path.exists() and binary_path.exists():
        assert result["status"] == "PASS"
    else:
        assert result["status"] == "FAIL"
        assert result["anchor"]["reason"] == "PRIMARY_BINARY_NOT_REPOSITORY_PINNED"
    assert result["anchor"]["expected_sha256"] == ANCHOR_SHA256
    assert result["contract"]["methodology"] == "SEEC"
    assert result["contract"]["rng"] == "numpy.PCG64"
    assert result["contract"]["seed"] == 20261006
    assert result["contract"]["min_mc_draws"] >= 10000
    assert result["contract"]["fail_closed"] is True
