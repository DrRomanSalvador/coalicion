from src.calibration import expanding_oos,accept_update
def test_oos_never_uses_future():
    r=expanding_oos([("2004",10),("2008",20),("2011",30)],lambda t:t[-1][1])
    assert [x.train_elections for x in r.folds]==[("2004",),("2004","2008")]
def test_equal_model_not_accepted():
    r=expanding_oos([("a",1),("b",2)],lambda t:t[-1][1])
    assert not accept_update(r,r)


def test_calibration_exposes_distribution_metrics():
    from src.calibration import expanding_oos
    s = expanding_oos([("e1", 10), ("e2", 12), ("e3", 9)], lambda train: train[-1][1] + 1)
    assert s.mae == 2.0
    assert s.rmse == (5.0) ** 0.5
    assert s.median_abs_error == 2.0
    assert s.max_abs_error == 3.0
    assert s.bias == 2.0
