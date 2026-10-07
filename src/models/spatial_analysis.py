"""Optional territorial diagnostics; never replaces legal seat allocation."""
from __future__ import annotations
import numpy as np
class SpatialElectoralModel:
    def __init__(self,geojson_path):
        try: from libpysal.weights import Queen
        except ImportError as exc: raise RuntimeError("libpysal is required") from exc
        self.w=Queen.from_file(geojson_path); self.w.transform="r"; self.rho=None; self.beta=None
    def fit_sar(self,y,X):
        try: from spreg import GM_Lag
        except ImportError as exc: raise RuntimeError("spreg is required") from exc
        m=GM_Lag(np.asarray(y),np.asarray(X),w=self.w); self.rho=float(m.rho); self.beta=np.asarray(m.betas).ravel()
        return {"rho":self.rho,"beta":self.beta.tolist(),"p_values":np.asarray(m.p_values).ravel().tolist(),"r_squared":float(m.pr2)}
    def predict_spatial(self,X_new,y_lag):
        if self.rho is None: raise RuntimeError("fit_sar must be called first")
        return self.rho*np.asarray(y_lag)+np.asarray(X_new)@self.beta[1:1+np.asarray(X_new).shape[1]]
    def moran_i(self,y):
        try: from esda.moran import Moran
        except ImportError as exc: raise RuntimeError("esda is required") from exc
        m=Moran(np.asarray(y),self.w); return {"moran_i":float(m.I),"p_value":float(m.p_sim),"z_score":float(m.z_sim)}
