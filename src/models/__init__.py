"""Methodological model extensions for COALICIÓN.

The canonical electoral/SEEC pipeline remains authoritative; these adapters are
opt-in and can be evaluated through OOS validation before promotion.
"""
from .ensemble import EnsembleModel
from .bayesian_ensemble import BayesianEnsemble
from .quantile_regression import QuantileRegressionForest
from .gaussian_process import GaussianProcessElectoral
from .conformal_prediction import ConformalPredictor
from .block_bootstrap import BlockBootstrap
from .robust_optimization import RobustEnsembleOptimizer
from .lstm_electoral import LSTM_ElectoralModel
from .causal_inference import CausalInference
from .spatial_analysis import SpatialElectoralModel

__all__ = [
    "EnsembleModel","BayesianEnsemble","QuantileRegressionForest",
    "GaussianProcessElectoral","ConformalPredictor","BlockBootstrap",
    "RobustEnsembleOptimizer","LSTM_ElectoralModel","CausalInference","SpatialElectoralModel",
]
