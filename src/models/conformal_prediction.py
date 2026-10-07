"""Temporal split-conformal prediction.

Calibration observations are kept separate from model fitting. This avoids the
in-sample residual leakage present in naive conformal implementations.
"""
from __future__ import annotations
import numpy as np

class ConformalPredictor:
    def __init__(self, base_model, alpha=0.05):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0,1)")
        self.base_model = base_model
        self.alpha = alpha
        self.nonconformity_scores = None
        self.calibration_size = 0

    def fit(self, X_train, y_train, X_calibration=None, y_calibration=None):
        X_train, y_train = np.asarray(X_train), np.asarray(y_train)
        if len(X_train) == 0 or len(X_train) != len(y_train):
            raise ValueError("training data are empty or misaligned")
        self.base_model.fit(X_train, y_train)
        if (X_calibration is None) != (y_calibration is None):
            raise ValueError("X_calibration and y_calibration must be supplied together")
        if X_calibration is None:
            # Ordered electoral data: reserve the latest 20% for calibration.
            split = max(1, int(np.floor(len(X_train) * 0.8)))
            if split == len(X_train):
                raise ValueError("need calibration observations")
            X_calibration, y_calibration = X_train[split:], y_train[split:]
            self.base_model.fit(X_train[:split], y_train[:split])
        X_calibration, y_calibration = np.asarray(X_calibration), np.asarray(y_calibration)
        if len(X_calibration) == 0 or len(X_calibration) != len(y_calibration):
            raise ValueError("calibration data are empty or misaligned")
        residuals = np.abs(y_calibration - self.base_model.predict(X_calibration))
        self.nonconformity_scores = np.sort(np.asarray(residuals, dtype=float))
        self.calibration_size = len(self.nonconformity_scores)
        return self

    def _q(self):
        if self.nonconformity_scores is None:
            raise RuntimeError("fit must be called first")
        n = self.calibration_size
        rank = int(np.ceil((n + 1) * (1 - self.alpha))) - 1
        return float(self.nonconformity_scores[min(max(rank, 0), n - 1)])

    def predict_interval(self, X_new):
        pred = np.asarray(self.base_model.predict(X_new))
        q = self._q()
        return pred - q, pred + q

    def predict_set(self, X_new, y_candidates):
        pred = np.asarray(self.base_model.predict(X_new))
        q = self._q()
        candidates = np.asarray(y_candidates)
        return candidates[np.abs(candidates - pred) <= q]
