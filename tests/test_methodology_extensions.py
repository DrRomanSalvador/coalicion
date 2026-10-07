import numpy as np
from src.models.ensemble import EnsembleModel
from src.models.bayesian_ensemble import BayesianEnsemble
from src.models.quantile_regression import QuantileRegressionForest
from src.models.gaussian_process import GaussianProcessElectoral
from src.models.conformal_prediction import ConformalPredictor
from src.models.block_bootstrap import BlockBootstrap
from src.models.robust_optimization import RobustEnsembleOptimizer
class MeanModel:
    def __init__(self): self.mean=None
    def fit(self,X,y): self.mean=float(np.mean(y)); return self
    def predict(self,X): return np.full(len(X),self.mean)
    def get_params(self): return {}
def data(): return np.arange(20,dtype=float).reshape(-1,1),np.linspace(0,1,20)
def test_ensembles():
    X,y=data()
    for cls in (EnsembleModel,BayesianEnsemble):
        m=cls([MeanModel(),MeanModel()]).fit(X,y); w=m.optimized_weights if isinstance(m,EnsembleModel) else m.model_weights
        assert np.isclose(w.sum(),1); assert len(m.predict(X))==20
def test_quantile_forest():
    X,y=data(); m=QuantileRegressionForest(n_trees=8,max_depth=3).fit(X,y); q=m.predict_quantiles(X,(.1,.5,.9))
    assert np.all(q[.1]<=q[.5]); assert np.all(q[.5]<=q[.9])
def test_gp():
    X,y=data(); mean,std=GaussianProcessElectoral().fit(X,y).predict(X); assert len(mean)==20 and np.all(std>=0)
def test_conformal():
    X,y=data(); lo,hi=ConformalPredictor(MeanModel()).fit(X,y).predict_interval(X); assert np.all(lo<=hi)
def test_block_bootstrap():
    X,y=data(); s=BlockBootstrap(4,1).resample(X,y,10); assert len(s)==10 and all(len(a)==20 for a,b in s)
def test_robust():
    X,y=data(); m=RobustEnsembleOptimizer([MeanModel(),MeanModel()]).fit(X,y,n_scenarios=5); assert np.isclose(m.robust_weights.sum(),1)
def test_optional_imports_are_lazy():
    from src.models.lstm_electoral import LSTM_ElectoralModel
    from src.models.causal_inference import CausalInference
    from src.models.spatial_analysis import SpatialElectoralModel
    assert LSTM_ElectoralModel and CausalInference and SpatialElectoralModel
