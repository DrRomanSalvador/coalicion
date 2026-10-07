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

__all__ = [
    "EnsembleModel","BayesianEnsemble","QuantileRegressionForest",
    "GaussianProcessElectoral","ConformalPredictor","BlockBootstrap",
    "RobustEnsembleOptimizer",
]
