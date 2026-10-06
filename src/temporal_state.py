"""Estado probabilístico temporal; conserva historial y actualiza incertidumbre."""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Mapping
@dataclass(frozen=True)
class StateSnapshot:
    timestamp:str; mean:Mapping[str,float]; variance:Mapping[str,float]; n_evidence:int; version:str="seec-state-1"
class TemporalState:
    def __init__(self,prior:Mapping[str,float],prior_variance:float=25.0):
        if not prior: raise ValueError("prior vacío")
        self._mean=dict(prior); self._var={p:float(prior_variance) for p in prior}; self._n=0; self.history=[]
    def update(self,timestamp:str,observation:Mapping[str,float],observation_variance:Mapping[str,float]):
        for p in set(self._mean)|set(observation):
            m0=self._mean.get(p,0.0); v0=self._var.get(p,25.0)
            if p not in observation: continue
            vo=float(observation_variance.get(p,25.0))
            if vo<=0: raise ValueError("varianza observacional debe ser > 0")
            self._mean[p]=(m0/v0+float(observation[p])/vo)/(1/v0+1/vo); self._var[p]=1/(1/v0+1/vo)
        self._n+=1; s=StateSnapshot(timestamp,dict(self._mean),dict(self._var),self._n); self.history.append(s); return s
    def uncertainty(self): return {p:sqrt(v) for p,v in self._var.items()}
