"""Bayesian model averaging utilities.

Weights use a numerically stable BIC approximation. This is model averaging,
not an assertion of Bayesian posterior calibration.
"""
from __future__ import annotations
import numpy as np

class BayesianEnsemble:
    def __init__(self, models):
        if not models:
            raise ValueError("at least one model is required")
        self.models = list(models)
        self.model_weights = None
        self.model_variances = None

    def fit(self, X_train, y_train):
        y = np.asarray(y_train, dtype=float)
        if y.ndim != 1 or len(y) == 0:
            raise ValueError("y_train must be a non-empty vector")
        log_likelihoods, variances = [], []
        for model in self.models:
            model.fit(X_train, y)
            residuals = y - np.asarray(model.predict(X_train), dtype=float)
            var = max(float(np.mean(residuals**2)), np.finfo(float).eps)
            variances.append(var)
            log_likelihoods.append(float(-0.5 * len(y) * (np.log(2*np.pi*var) + 1.0)))
        k = [len(m.get_params()) if hasattr(m, "get_params") else 1 for m in self.models]
        bic = np.asarray([-2*ll + ki*np.log(len(y)) for ll, ki in zip(log_likelihoods, k)])
        z = -0.5 * (bic - np.min(bic))
        weights = np.exp(z)
        self.model_weights = weights / weights.sum()
        self.model_variances = np.asarray(variances)
        return self

    def _check_fitted(self):
        if self.model_weights is None:
            raise RuntimeError("fit must be called first")

    def predict(self, X):
        self._check_fitted()
        preds = np.asarray([m.predict(X) for m in self.models], dtype=float)
        return np.average(preds, axis=0, weights=self.model_weights)

    def predict_distribution(self, X, n_samples=10000, random_state=20261008):
        self._check_fitted()
        if n_samples < 1:
            raise ValueError("n_samples must be positive")
        rng = np.random.default_rng(random_state)
        preds = np.asarray([m.predict(X) for m in self.models], dtype=float)
        idx = rng.choice(len(self.models), size=n_samples, p=self.model_weights)
        noise = rng.normal(0.0, np.sqrt(self.model_variances[idx])[:, None], size=(n_samples, preds.shape[1] if preds.ndim > 1 else 1))
        chosen = preds[idx]
        return chosen + noise if chosen.ndim > 1 else chosen + noise[:, 0]
