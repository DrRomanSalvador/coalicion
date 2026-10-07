"""Bootstrap quantile regression forest adapter.

The implementation exposes empirical quantiles of independently seeded forest
predictions. It is an uncertainty estimator, not a claim of exact coverage.
"""
from __future__ import annotations
import numpy as np

class QuantileRegressionForest:
    def __init__(self, n_trees=200, max_depth=10, random_state=20261008):
        if n_trees < 1:
            raise ValueError("n_trees must be positive")
        self.n_trees, self.max_depth, self.random_state = n_trees, max_depth, random_state
        self.trees = []

    def fit(self, X, y):
        try:
            from sklearn.tree import DecisionTreeRegressor
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required for QuantileRegressionForest") from exc
        X, y = np.asarray(X), np.asarray(y)
        self.trees = []
        rng = np.random.default_rng(self.random_state)
        for _ in range(self.n_trees):
            idx = rng.integers(0, len(y), size=len(y))
            tree = DecisionTreeRegressor(max_depth=self.max_depth, random_state=int(rng.integers(0, 2**31-1)))
            tree.fit(X[idx], y[idx])
            self.trees.append(tree)
        return self

    def predict_quantiles(self, X, quantiles=(0.025, 0.5, 0.975)):
        if not self.trees:
            raise RuntimeError("fit must be called first")
        q = np.asarray(quantiles, dtype=float)
        if np.any((q < 0) | (q > 1)):
            raise ValueError("quantiles must be in [0,1]")
        predictions = np.asarray([tree.predict(X) for tree in self.trees])
        return {float(level): np.quantile(predictions, level, axis=0) for level in q}

    def predict_interval(self, X, confidence=0.95):
        if not 0 < confidence < 1:
            raise ValueError("confidence must be in (0,1)")
        a = (1-confidence)/2
        return self.predict_quantiles(X, (a, 0.5, 1-a))
