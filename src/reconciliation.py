"""Reconciliación fail-closed de fuentes electorales."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
@dataclass(frozen=True)
class Reconciliation:
    keys:int; mismatches:int; max_abs_diff:float; status:str
def reconcile(primary:Mapping[tuple[str,str],float], replica:Mapping[tuple[str,str],float], tolerance:float=0.0)->Reconciliation:
    keys=sorted(set(primary)|set(replica)); mismatches=0; mx=0.0
    for k in keys:
        d=abs(float(primary.get(k,0))-float(replica.get(k,0))); mx=max(mx,d)
        if d>tolerance: mismatches+=1
    return Reconciliation(len(keys),mismatches,mx,"PASS" if mismatches==0 else "FAIL")
