from src.uncertainty import SimulationConfig,run_monte_carlo
def test_mc_minimum():
    try: run_monte_carlo(lambda rng:{"A":{"A":100}},{"A":1},{"A":0},{"A":"Ceuta"},SimulationConfig(9999))
    except ValueError: pass
    else: raise AssertionError
def test_mc_reproducible():
    cfg=SimulationConfig(10000,42)
    s=lambda rng:{"A":{"A":100}}
    args=({"A":1},{"A":0},{"A":"Ceuta"})
    assert run_monte_carlo(s,*args,cfg)==run_monte_carlo(s,*args,cfg)

def test_mc_default_matches_canonical_reproducibility_contract():
    from src.reproducibility_contract import ExecutionContract
    config = SimulationConfig()
    assert config.seed == ExecutionContract.seed
    assert config.rng_algorithm == ExecutionContract.rng


def test_mc_rejects_rng_metadata_that_does_not_match_implementation():
    import pytest
    config = SimulationConfig(10000, 42, "numpy.MT19937")
    with pytest.raises(ValueError, match="algoritmo RNG no implementado"):
        run_monte_carlo(lambda rng: {"A": {"A": 100}}, {"A": 1}, {"A": 0},
                        {"A": "Ceuta"}, config)


def test_mc_rejects_boolean_seed():
    import pytest
    config = SimulationConfig(10000, True)
    with pytest.raises(ValueError, match="semilla"):
        run_monte_carlo(lambda rng: {"A": {"A": 100}}, {"A": 1}, {"A": 0},
                        {"A": "Ceuta"}, config)
