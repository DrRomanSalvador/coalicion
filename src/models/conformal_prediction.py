"""Split-conformal prediction with finite-sample quantile correction."""
from __future__ import annotations
import numpy as np

class ConformalPredictor:
    def __init__(self, base_model, alpha=0.05):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0,1)")
        self.base_model, self.alpha, self.nonconformity_scores = base_model, alpha, None

    def fit(self, X_train, y_train):
        self.base_model.fit(X_train, y_train)
        residuals = np.abs(np.asarray(y_train) - np.asarray(self.base_model.predict(X_train)))
        self.nonconformity_scores = np.sort(residuals)
        return self

    def _q(self):
        if self.nonconformity_scores is None:
            raise RuntimeError("fit must be called first")
        n = len(self.nonconformity_scores)
        rank = min(n, int(np.ceil((n+1)*(1-self.alpha)))) - 1
        return float(self.nonconformity_scores[max(0, rank)])

    def predict_interval(self, X_new):
        pred = np.asarray(self.base_model.predict(X_new))
        q = self._q()
        return pred-q, pred+q

    def predict_set(self, X_new, y_candidates):
        pred = np.asarray(self.base_model.predict(X_new))
        q = self._q()
        candidates = np.asarray(y_candidates)
        return candidates[np.abs(candidates-pred) <= q]
