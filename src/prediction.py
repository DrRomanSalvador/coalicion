"""Único módulo estadístico: error, calibración, sesgos y transformación de votos."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date
from math import sqrt
from statistics import mean, median
from typing import Callable, Iterable, Mapping, Sequence
from .data import PollObservation
from .electoral import allocate

@dataclass(frozen=True)
class TurnoutScenario:
    name: str
    turnout: float
    basis: str

def historical_turnout_scenarios(turnouts: list[float], window: int = 5) -> list[TurnoutScenario]:
    vals = [float(x) for x in turnouts if 0 < float(x) < 1]
    if not vals: raise ValueError("Se necesitan participaciones históricas")
    vals = vals[-window:]
    ordered = sorted(vals); n = len(ordered)
    return [
        TurnoutScenario("baja", ordered[int((n-1)*.25)], f"percentil_25_últimos_{n}"),
        TurnoutScenario("central", ordered[int((n-1)*.50)], f"mediana_últimos_{n}"),
        TurnoutScenario("alta", ordered[int((n-1)*.75)], f"percentil_75_últimos_{n}"),
    ]

def _integer_scale(votes: Mapping[str, int], factor: float) -> dict[str, int]:
    if factor < 0: raise ValueError("factor inválido")
    return {p: max(0, int(round(v * factor))) for p, v in votes.items()}

def rescale_votes_by_turnout(votes: Mapping[str, int], observed_turnout: float, target_turnout: float) -> dict[str, int]:
    if not 0 < observed_turnout <= 1 or not 0 < target_turnout <= 1:
        raise ValueError("participación fuera de rango")
    return _integer_scale(votes, target_turnout / observed_turnout)

def simulate_constituency(votes: Mapping[str, int], seats: int, blank: int, target_turnout_factor: float = 1.0) -> dict:
    adjusted = _integer_scale(votes, target_turnout_factor)
    result = allocate(adjusted, seats, sum(adjusted.values()) + blank, blank_votes=blank)
    if result.status != "OK": raise RuntimeError(result.status)
    return {"votes": adjusted, "seats": result.seats}

def build_scenario_catalog(historical_turnouts: list[float]) -> list[dict]:
    return [asdict(x) for x in historical_turnout_scenarios(historical_turnouts)]

@dataclass(frozen=True)
class Score:
    mae: float
    rmse: float
    max_abs: float

@dataclass(frozen=True)
class Candidate:
    name: str
    predict: Callable[[Sequence[PollObservation], PollObservation], float]

def _score(errors: Sequence[float]) -> Score:
    if not errors: raise ValueError("No hay observaciones de validación")
    return Score(sum(abs(x) for x in errors)/len(errors),
                 sqrt(sum(x*x for x in errors)/len(errors)),
                 max(abs(x) for x in errors))

def _date(x: PollObservation) -> date:
    if not x.field_end: raise ValueError("field_end es obligatorio para validación temporal")
    return date.fromisoformat(x.field_end)

def base(train: Sequence[PollObservation], obs: PollObservation) -> float:
    return obs.poll

def _common_bias(train: Sequence[PollObservation]) -> float:
    return median([x.actual-x.poll for x in train]) if train else 0.0

def robust_party_bias(train: Sequence[PollObservation], party: str, shrink_k: float = 3.0) -> float:
    errors=[x.actual-x.poll for x in train if x.party==party]
    if not errors: return _common_bias(train)
    w=len(errors)/(len(errors)+shrink_k)
    return w*median(errors)+(1-w)*_common_bias(train)

def additive_common(train, obs): return obs.poll + _common_bias(train)
def additive_party(train, obs): return obs.poll + robust_party_bias(train, obs.party)

def _temporal_folds(observations: Sequence[PollObservation]):
    ordered=sorted(observations,key=_date)
    elections=[]
    for x in ordered:
        if x.election not in elections: elections.append(x.election)
    for election in elections:
        test=[x for x in ordered if x.election==election]
        train=[x for x in ordered if _date(x)<min(_date(t) for t in test)]
        if train: yield train,test

def _errors(candidate: Candidate, observations: Sequence[PollObservation]):
    base_scores=[]; candidate_scores=[]
    for train,test in _temporal_folds(observations):
        base_scores.append(_score([x.poll-x.actual for x in test]))
        candidate_scores.append(_score([candidate.predict(train,x)-x.actual for x in test]))
    if not base_scores: raise ValueError("No existe ventana OOS entrenable")
    macro=lambda xs: Score(*(sum(getattr(x,k) for x in xs)/len(xs) for k in ("mae","rmse","max_abs")))
    return macro(base_scores),macro(candidate_scores)

def dominates(base_score: Score, candidate_score: Score) -> bool:
    fields=("mae","rmse","max_abs")
    return all(getattr(candidate_score,f)<=getattr(base_score,f) for f in fields) and any(
        getattr(candidate_score,f)<getattr(base_score,f) for f in fields)

def select_best(observations: Sequence[PollObservation]) -> Candidate:
    candidates=[Candidate("BASE",base),Candidate("BIAS_COMUN",additive_common),
                Candidate("BIAS_PARTIDO_SHRINK",additive_party)]
    bs,_=_errors(candidates[0],observations); accepted=[]
    for candidate in candidates[1:]:
        _,cs=_errors(candidate,observations)
        if dominates(bs,cs): accepted.append((candidate,cs))
    return min(accepted,key=lambda z:(z[1].mae,z[1].rmse,z[1].max_abs))[0] if accepted else candidates[0]

@dataclass(frozen=True)
class CalibrationFold:
    election: str; train_elections: tuple[str,...]; actual: float; predicted: float; error: float

@dataclass(frozen=True)
class CalibrationSummary:
    folds: tuple[CalibrationFold,...]; mae: float; rmse: float

def expanding_oos(observations, predictor, min_train_elections=1):
    if min_train_elections<1 or not observations: raise ValueError("configuración OOS inválida")
    folds=[]
    for i,(election,actual) in enumerate(observations):
        train=observations[:i]
        if len(train)<min_train_elections: continue
        pred=float(predictor(train))
        folds.append(CalibrationFold(election,tuple(e for e,_ in train),float(actual),pred,pred-float(actual)))
    if not folds: raise ValueError("no existe ventana OOS entrenable")
    errors=[f.error for f in folds]
    return CalibrationSummary(tuple(folds),sum(abs(e) for e in errors)/len(errors),
                              sqrt(sum(e*e for e in errors)/len(errors)))

def accept_update(base_score, candidate_score, max_mae_increase=0.0, max_rmse_increase=0.0):
    if candidate_score.mae>base_score.mae+max_mae_increase or candidate_score.rmse>base_score.rmse+max_rmse_increase: return False
    return candidate_score.mae<base_score.mae or candidate_score.rmse<base_score.rmse

@dataclass(frozen=True)
class ErrorSummary:
    n:int; mean_error:float; median_error:float; mae:float; rmse:float
    minimum:float; maximum:float; p50_abs:float; p80_abs:float; p90_abs:float; p95_abs:float

def _quantile(values, q):
    if not values: raise ValueError("No hay observaciones")
    x=sorted(values); pos=(len(x)-1)*q; lo=int(pos); hi=min(lo+1,len(x)-1)
    return x[lo]+(x[hi]-x[lo])*(pos-lo)

def summarize(observations: Iterable[PollObservation]) -> ErrorSummary:
    rows=list(observations)
    if not rows: raise ValueError("No hay observaciones")
    errors=[x.error for x in rows]; ae=[abs(x) for x in errors]
    return ErrorSummary(len(errors),mean(errors),median(errors),mean(ae),sqrt(mean(x*x for x in errors)),
                        min(errors),max(errors),_quantile(ae,.5),_quantile(ae,.8),_quantile(ae,.9),_quantile(ae,.95))

def _group(rows, key):
    groups={}
    for row in rows: groups.setdefault(key(row),[]).append(row)
    return {k:summarize(v) for k,v in sorted(groups.items())}

def by_election(rows): return _group(rows,lambda r:r.election)
def by_party(rows): return _group(rows,lambda r:r.party)
def by_house(rows): return _group(rows,lambda r:r.house)
def by_government(rows): return _group(rows,lambda r:r.governing_party or "DESCONOCIDO")
def by_government_status(rows): return _group(rows,lambda r:r.government_status or "DESCONOCIDO")
def by_direction(rows): return _group(rows,lambda r:r.error_direction)

def by_days_to_election(rows,bins=(1,3,7,14,30,60)):
    return _group(rows,lambda r:next((f"<= {b}d" for b in bins if r.days_to_election<=b),f"> {bins[-1]}d"))

def leave_one_election_out(rows):
    result={}
    for train,test in _temporal_folds(rows):
        election=test[0].election; bias=median([r.actual-r.poll for r in train])
        result[election]={"base_mae":mean([abs(r.poll-r.actual) for r in test]),
                           "corrected_mae":mean([abs(r.poll+bias-r.actual) for r in test]),"bias":bias}
    return result

@dataclass(frozen=True)
class ChangeSummary:
    election:str; party:str; actual_change:float; poll_change:float; change_error:float

def change_vs_previous_election(rows):
    elections=sorted({r.election for r in rows},key=lambda e:min(r.election_date for r in rows if r.election==e))
    by_key={(r.election,r.party):r for r in rows}; out=[]
    for i in range(1,len(elections)):
        prev,cur=elections[i-1],elections[i]
        for party in sorted({p for e,p in by_key if e==cur}&{p for e,p in by_key if e==prev}):
            old,new=by_key[(prev,party)],by_key[(cur,party)]
            actual_change=new.actual-old.actual; poll_change=new.poll-old.actual
            out.append(ChangeSummary(cur,party,actual_change,poll_change,poll_change-actual_change))
    return out

def direction_counts(rows):
    out={"SOBREESTIMACION":0,"SUBESTIMACION":0,"CERO":0}
    for row in rows: out[row.error_direction]+=1
    return out

@dataclass(frozen=True)
class ContextScore:
    mae:float; rmse:float; n_elections:int

def _context_bias(rows,key,value,shrink=3.0):
    all_errors=[r.actual-r.poll for r in rows]; group=[r.actual-r.poll for r in rows if key(r)==value]
    common=median(all_errors) if all_errors else 0.0
    if not group:return common
    w=len(group)/(len(group)+shrink)
    return w*median(group)+(1-w)*common

def _context_predict(train,obs,dimensions):
    def key(r):
        vals={"house":r.house,"party":r.party,"government":r.governing_party,"status":r.government_status}
        return "|".join(vals[d] for d in dimensions)
    value=key(obs)
    return obs.poll+_context_bias(train,key,value)

def candidate_names():
    return ("BASE","HOUSE","PARTY","GOVERNMENT","HOUSE_PARTY","GOVERNMENT_PARTY")

def predict(name,train,obs):
    if name=="BASE":return obs.poll
    dims={"HOUSE":("house",),"PARTY":("party",),"GOVERNMENT":("government",),
          "HOUSE_PARTY":("house","party"),"GOVERNMENT_PARTY":("government","party")}
    if name not in dims: raise ValueError(f"Candidato desconocido: {name}")
    return _context_predict(train,obs,dims[name])

def evaluate(rows):
    out={}
    for name in candidate_names():
        maes=[];rmses=[]
        for train,test in _temporal_folds(rows):
            errors=[predict(name,train,r)-r.actual for r in test]
            maes.append(mean(abs(e) for e in errors)); rmses.append(sqrt(mean(e*e for e in errors)))
        if maes: out[name]=ContextScore(mean(maes),mean(rmses),len(maes))
    return out

def select(rows):
    scores=evaluate(rows)
    if "BASE" not in scores:return "BASE"
    base_score=scores["BASE"]
    candidates=[(n,s) for n,s in scores.items() if n!="BASE" and s.mae<=base_score.mae and s.rmse<=base_score.rmse and (s.mae<base_score.mae or s.rmse<base_score.rmse)]
    return min(candidates,key=lambda x:(x[1].mae,x[1].rmse))[0] if candidates else "BASE"

@dataclass(frozen=True)
class ErrorDecomposition:
    election:str; party:str; house:str; total_error:float; sector_error:float; house_component:float; residual:float

def decompose_sector_house(rows):
    groups={}
    for r in rows: groups.setdefault((r.election,r.party),[]).append(r)
    out=[]
    for (election,party),group in sorted(groups.items()):
        sector=mean(r.error for r in group)
        out.extend(ErrorDecomposition(election,party,r.house,r.error,sector,r.error-sector,0.0) for r in group)
    return out

@dataclass(frozen=True)
class MovementDecomposition:
    election:str; party:str; previous_actual:float; actual_change:float; observed_change:float; level_error:float; movement_error:float

def decompose_movement(rows):
    by_key={}
    for r in rows:
        key=(r.election,r.party)
        if key in by_key: raise ValueError("decompose_movement requiere una observación agregada por elección/partido")
        by_key[key]=r
    elections=sorted({r.election for r in rows},key=lambda e:min(r.election_date for r in rows if r.election==e))
    out=[]
    for i in range(1,len(elections)):
        prev,cur=elections[i-1],elections[i]
        for party in sorted({p for e,p in by_key if e==prev}&{p for e,p in by_key if e==cur}):
            old,new=by_key[(prev,party)],by_key[(cur,party)]
            actual_change=new.actual-old.actual; observed_change=new.poll-old.actual
            out.append(MovementDecomposition(cur,party,old.actual,actual_change,observed_change,new.error,observed_change-actual_change))
    return out

@dataclass(frozen=True)
class FalsificationResult:
    claim:str; status:str; n:int; mae:float; rmse:float; median_error:float; max_abs_error:float

def falsification_metrics(rows):
    if not rows: raise ValueError("No hay observaciones")
    e=[r.error for r in rows]
    return FalsificationResult("La distribución observada del error es reproducible con los datos documentados","TESTABLE",
                               len(e),mean(abs(x) for x in e),sqrt(mean(x*x for x in e)),median(e),max(abs(x) for x in e))
