"""Calibración estrictamente OOS mediante ventana expansiva."""
from dataclasses import dataclass
@dataclass(frozen=True)
class CalibrationFold:
    election:str; train_elections:tuple[str,...]; actual:float; predicted:float; error:float
@dataclass(frozen=True)
class CalibrationSummary:
    folds:tuple[CalibrationFold,...]; mae:float; rmse:float
def expanding_oos(observations,predictor,min_train_elections=1):
    if min_train_elections<1 or not observations: raise ValueError("configuración OOS inválida")
    folds=[]
    for i,(election,actual) in enumerate(observations):
        train=observations[:i]
        if len(train)<min_train_elections: continue
        pred=float(predictor(train))
        folds.append(CalibrationFold(election,tuple(e for e,_ in train),float(actual),pred,pred-float(actual)))
    if not folds: raise ValueError("no existe ventana OOS entrenable")
    es=[f.error for f in folds]
    return CalibrationSummary(tuple(folds),sum(abs(e) for e in es)/len(es),(sum(e*e for e in es)/len(es))**.5)
def accept_update(base,candidate,max_mae_increase=0.0,max_rmse_increase=0.0):
    if candidate.mae>base.mae+max_mae_increase or candidate.rmse>base.rmse+max_rmse_increase: return False
    return candidate.mae<base.mae or candidate.rmse<base.rmse
