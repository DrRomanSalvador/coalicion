"""Deterministic constrained ensemble weighting."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize

class EnsembleModel:
    def __init__(self, models, weights="optimal"):
        if not models: raise ValueError("at least one model is required")
        self.models=list(models); self.weights=weights; self.optimized_weights=None

    def fit(self,X_train,y_train):
        for m in self.models: m.fit(X_train,y_train)
        if self.weights=="optimal":
            def loss(w):
                p=np.average([m.predict(X_train) for m in self.models],axis=0,weights=w)
                return float(np.mean((p-np.asarray(y_train))**2))
            r=minimize(loss,np.full(len(self.models),1/len(self.models)),method="SLSQP",
                       bounds=[(0,1)]*len(self.models),constraints={"type":"eq","fun":lambda w:np.sum(w)-1})
            if not r.success: raise RuntimeError(f"ensemble optimization failed: {r.message}")
            self.optimized_weights=r.x
        else:
            self.optimized_weights=np.full(len(self.models),1/len(self.models))
        return self

    def predict(self,X):
        if self.optimized_weights is None: raise RuntimeError("fit must be called first")
        return np.average([m.predict(X) for m in self.models],axis=0,weights=self.optimized_weights)
