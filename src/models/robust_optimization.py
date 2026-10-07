"""Robust non-negative ensemble weighting."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize

class RobustEnsembleOptimizer:
    def __init__(self, models):
        if not models: raise ValueError("at least one model is required")
        self.models=list(models); self.robust_weights=None

    def fit(self, X_train, y_train, n_scenarios=100, random_state=20261008):
        X,y=np.asarray(X_train),np.asarray(y_train)
        rng=np.random.default_rng(random_state)
        scenarios=[]
        for _ in range(n_scenarios):
            idx=rng.integers(0,len(y),size=len(y))
            scenarios.append((X[idx],y[idx]))
        for m in self.models: m.fit(X,y)
        def objective(w):
            return max(float(np.mean(np.abs(np.average([m.predict(xs) for m in self.models],axis=0,weights=w)-ys))) for xs,ys in scenarios)
        result=minimize(objective,np.full(len(self.models),1/len(self.models)),method="SLSQP",
                        bounds=[(0,1)]*len(self.models),
                        constraints={"type":"eq","fun":lambda w:np.sum(w)-1})
        if not result.success: raise RuntimeError(f"robust optimization failed: {result.message}")
        self.robust_weights=result.x
        return self

    def predict(self,X):
        if self.robust_weights is None: raise RuntimeError("fit must be called first")
        return np.average([m.predict(X) for m in self.models],axis=0,weights=self.robust_weights)
