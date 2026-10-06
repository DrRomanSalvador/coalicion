from pathlib import Path
from src.reproducibility_contract import ANCHOR_SHA256, ANCHOR_MANIFEST, verify_contract

def test_reproducibility_contract_is_fail_closed():
    result = verify_contract(Path("."))
    assert result["status"] == "PASS"
    assert result["anchor"]["sha256"] == ANCHOR_SHA256
    assert result["contract"]["methodology"] == "SEEC"
    assert result["contract"]["rng"] == "numpy.PCG64"
    assert result["contract"]["seed"] == 20261006
    assert result["contract"]["min_mc_draws"] >= 10000
    assert result["contract"]["fail_closed"] is True
    assert ANCHOR_MANIFEST.exists()