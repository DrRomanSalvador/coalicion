import numpy as np
from sklearn.linear_model import LinearRegression

from src.models import (
    EnsembleModel, BayesianEnsemble, QuantileRegressionForest,
    GaussianProcessElectoral, ConformalPredictor, BlockBootstrap,
    RobustEnsembleOptimizer,
)

def data():
    x = np.arange(40, dtype=float).reshape(-1, 1)
    y = 2*x[:, 0] + 1
    return x, y

def test_ensemble_and_bma_are_deterministic():
    X,y=data()
    a=EnsembleModel([LinearRegression(), LinearRegression()]).fit(X,y)
    b=BayesianEnsemble([LinearRegression(), LinearRegression()]).fit(X,y)
    assert np.allclose(a.predict(X), y)
    assert np.allclose(b.predict(X), y)

def test_quantile_forest_and_gp_fit():
    X,y=data()
    q=QuantileRegressionForest(n_trees=8,max_depth=4).fit(X,y)
    out=q.predict_interval(X[:3])
    assert np.allclose(sorted(out), [0.025,0.5,0.975])
    gp=GaussianProcessElectoral().fit(X,y)
    mean,std=gp.predict(X[:3])
    assert mean.shape==std.shape==(3,)

def test_conformal_uses_temporal_calibration_split():
    X,y=data()
    c=ConformalPredictor(LinearRegression(),alpha=.1).fit(X[:30],y[:30],X[30:],y[30:])
    lo,hi=c.predict_interval(X[35:38])
    assert np.all(lo<=hi)

def test_block_bootstrap_preserves_shape():
    X,y=data()
    samples=BlockBootstrap(block_length=5,random_state=1).resample(X,y,4)
    assert len(samples)==4
    assert all(a.shape==X.shape and b.shape==y.shape for a,b in samples)

def test_robust_optimizer_weights_sum_to_one():
    X,y=data()
    r=RobustEnsembleOptimizer([LinearRegression(),LinearRegression()]).fit(X,y,n_scenarios=4,random_state=1)
    assert np.isclose(r.robust_weights.sum(),1)
    assert np.all(r.robust_weights>=0)
