"""Gaussian-process uncertainty adapter."""
from __future__ import annotations
import numpy as np

class GaussianProcessElectoral:
    def __init__(self, random_state=20261008):
        self.random_state = random_state
        self.gp = None

    def fit(self, X, y):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
        kernel = ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(0.1)
        self.gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2, random_state=self.random_state)
        self.gp.fit(X, y)
        return self

    def _check(self):
        if self.gp is None:
            raise RuntimeError("fit must be called first")

    def predict(self, X, return_std=True):
        self._check()
        return self.gp.predict(X, return_std=return_std)

    def predict_with_uncertainty(self, X, n_samples=1000, random_state=20261008):
        self._check()
        mean, cov = self.gp.predict(X, return_cov=True)
        rng = np.random.default_rng(random_state)
        cov = cov + np.eye(len(mean))*1e-10
        return rng.multivariate_normal(mean, cov, size=n_samples)

    def acquisition_function(self, X_candidate, X_train, y_train):
        from scipy.stats import norm
        self.fit(X_train, y_train)
        mean, std = self.predict(X_candidate, return_std=True)
        std = np.maximum(std, 1e-12)
        z = (mean - np.max(y_train)) / std
        return (mean - np.max(y_train))*norm.cdf(z) + std*norm.pdf(z)
