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
