from src.prediction import expanding_oos,accept_update

def test_oos_never_uses_future():
    r=expanding_oos([("2004",10),("2008",20),("2011",30)],lambda t:t[-1][1])
    assert [x.train_elections for x in r.folds]==[("2004",),("2004","2008")]

def test_equal_model_not_accepted():
    r=expanding_oos([("a",1),("b",2)],lambda t:t[-1][1])
    assert not accept_update(r,r)
