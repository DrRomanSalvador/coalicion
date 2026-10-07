import numpy as np
from sklearn.linear_model import LinearRegression
from src.methodology_bridge import evaluate_candidates, candidate_summary

def test_candidate_is_evaluated_on_future_holdout():
    x=np.arange(30,dtype=float).reshape(-1,1)
    y=2*x[:,0]+1
    result=evaluate_candidates([LinearRegression()],x[:20],y[:20],x[20:],y[20:])[0]
    assert result["oos"]=="PASS"
    assert result["leakage_free"] is True
    assert result["n_train"]==20 and result["n_test"]==10

def test_oos_does_not_promote_without_calibration():
    result=candidate_summary([{"candidate":"LinearRegression","oos":"PASS","mae":0.0}])
    assert result["promotion"]=="BLOCKED_UNTIL_CALIBRATED"
