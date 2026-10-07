from pathlib import Path
from src.reproducibility_contract import ANCHOR_SHA256, ANCHOR_MANIFEST, ANCHOR_BINARY, verify_contract

def test_reproducibility_contract_is_fail_closed():
    result = verify_contract(Path("."))
    if Path(ANCHOR_BINARY).exists():
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
