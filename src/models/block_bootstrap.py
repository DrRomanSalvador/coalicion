"""Moving block bootstrap for ordered electoral time series."""
from __future__ import annotations
import numpy as np

class BlockBootstrap:
    def __init__(self, block_length=7, random_state=20261008):
        if block_length < 1:
            raise ValueError("block_length must be positive")
        self.block_length, self.random_state = block_length, random_state

    def resample(self, X, y, n_bootstrap=1000):
        X, y = np.asarray(X), np.asarray(y)
        n = len(y)
        if n == 0 or len(X) != n:
            raise ValueError("X and y must have equal non-zero length")
        if self.block_length > n:
            raise ValueError("block_length cannot exceed sample length")
        rng = np.random.default_rng(self.random_state)
        starts = np.arange(0, n-self.block_length+1)
        blocks = int(np.ceil(n/self.block_length))
        out=[]
        for _ in range(n_bootstrap):
            chosen = rng.choice(starts, size=blocks, replace=True)
            xb=np.vstack([X[s:s+self.block_length] for s in chosen])[:n]
            yb=np.concatenate([y[s:s+self.block_length] for s in chosen])[:n]
            out.append((xb,yb))
        return out

    def predict_with_uncertainty(self, model, X, y, X_test, n_bootstrap=1000):
        predictions=[]
        for xb,yb in self.resample(X,y,n_bootstrap):
            model.fit(xb,yb)
            predictions.append(model.predict(X_test))
        p=np.asarray(predictions)
        return np.mean(p,axis=0), np.quantile(p,.025,axis=0), np.quantile(p,.975,axis=0)
