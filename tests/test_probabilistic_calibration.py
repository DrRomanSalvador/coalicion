from src.probabilistic_calibration import evaluate


def test_brier_and_coverage():
    r=evaluate([1,0,1,0],[0.9,0.2,0.8,0.1],[0,0,0,0],[1,1,1,1])
    assert r.brier < 0.05
    assert r.coverage == 1.0
