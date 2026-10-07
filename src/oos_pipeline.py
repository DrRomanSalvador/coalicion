"""Expanding-window OOS pipeline with strict temporal isolation."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from .bias_filter import Observation, select_best
from .context_corrections import predict as predict_context, select
from .poll_error import PollObservation

ELECTIONS = (
    ("2004-03-14", "2004"),
    ("2008-03-09", "2008"),
    ("2011-11-20", "2011"),
    ("2015-12-20", "2015"),
    ("2016-06-26", "2016"),
    ("2019-04-28", "2019A"),
    ("2019-11-10", "2019N"),
    ("2023-07-23", "2023J"),
)
ELECTION_DATES = dict(ELECTIONS)
CANONICAL = {"fecha_encuesta", "partido", "estimacion_voto", "tipo_encuesta", "fuente", "codigo_estudio"}
LEGACY = {"election", "election_date", "party", "poll", "actual", "house", "field_end", "source", "poll_id"}
ALIAS = {
    "psoe": "PSOE", "partido socialista obrero espanol": "PSOE", "pp": "PP",
    "partido popular": "PP", "vox": "VOX", "sumar": "SUMAR", "podemos": "PODEMOS",
    "iu": "IU", "izquierda unida": "IU", "cs": "CS", "ciudadanos": "CS", "erc": "ERC",
    "esquerra republicana de catalunya": "ERC", "junts": "JUNTS", "junts per catalunya": "JUNTS",
    "pnv": "PNV", "partido nacionalista vasco": "PNV", "bildu": "EH_BILDU",
    "eh bildu": "EH_BILDU", "bng": "BNG", "bloque nacionalista galego": "BNG",
}


def _norm(v: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", v.lower()).strip()
    s = re.sub(r"\s+", " ", s)
    return ALIAS.get(s, s.upper().replace(" ", "_"))


def _next(d: date):
    for raw, code in ELECTIONS:
        if d < date.fromisoformat(raw):
            return raw, code
    return None


def _election_key(row):
    raw = (row.get("election") or "").strip()
    if raw in ELECTION_DATES:
        return raw
    raw_date = (row.get("fecha_eleccion") or "").strip()[:10]
    for election_date, code in ELECTIONS:
        if raw_date == election_date:
            return code
    raise ValueError(f"official row has unknown election/date: {row}")


def _official(path: Path) -> dict[tuple[str, str], float]:
    if not path.exists():
        raise FileNotFoundError(f"official results required for canonical OOS: {path}")
    totals: dict[tuple[str, str], float] = {}
    national: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("official results CSV has no header")
        required = {"partido", "votos"}
        if not required.issubset(reader.fieldnames):
            raise ValueError(f"official results missing columns: {sorted(required - set(reader.fieldnames))}")
        for row in reader:
            election = _election_key(row)
            party = _norm(row["partido"])
            try:
                votes = float(row["votos"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid official votes: {row}") from exc
            if votes < 0:
                raise ValueError("negative official votes")
            totals[(election, party)] = totals.get((election, party), 0.0) + votes
            national[election] = national.get(election, 0.0) + votes
    if set(national) != set(ELECTION_DATES):
        raise ValueError(f"official OOS scope mismatch: {sorted(national)}")
    return {
        key: 100.0 * votes / national[key[0]]
        for key, votes in totals.items()
        if national[key[0]] > 0
    }


def _canonical(rows, actual_path: Path) -> list[PollObservation]:
    actuals = _official(actual_path)
    out: list[PollObservation] = []
    for row in rows:
        try:
            field_end = date.fromisoformat(row["fecha_encuesta"][:10])
            estimate = float(row["estimacion_voto"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid canonical CIS row: {row}") from exc
        if row.get("tipo_encuesta", "").strip().lower() == "postelectoral":
            continue
        target = _next(field_end)
        if not target:
            continue
        election_date, election = target
        if field_end >= date.fromisoformat(election_date):
            raise ValueError(f"future leakage: poll date {field_end} is not before {election_date}")
        party = _norm(row["partido"])
        actual = actuals.get((election, party))
        if actual is None:
            continue
        out.append(PollObservation(
            election=election, election_date=election_date, party=party,
            poll=estimate, actual=actual, house="Congreso", field_end=field_end.isoformat(),
            source=row["fuente"], poll_id=f"{row['codigo_estudio']}:{party}",
        ))
    if not out:
        raise ValueError("canonical CIS dataset produced zero pre-election OOS observations")
    return out


def _legacy(rows) -> list[PollObservation]:
    missing = LEGACY - set(rows[0])
    if missing:
        raise ValueError(f"legacy OOS dataset missing columns: {sorted(missing)}")
    out = []
    for row in rows:
        field_end = date.fromisoformat(row["field_end"][:10])
        election_date = date.fromisoformat(row["election_date"][:10])
        if field_end >= election_date:
            raise ValueError(f"future leakage in legacy row: {row}")
        out.append(PollObservation(
            election=row["election"], election_date=election_date.isoformat(),
            party=row["party"], poll=float(row["poll"]), actual=float(row["actual"]),
            house=row["house"], field_end=field_end.isoformat(), source=row["source"],
            poll_id=row["poll_id"], governing_party=row.get("governing_party", ""),
            government_status=row.get("government_status", ""),
            government_change=row.get("government_change", ""),
        ))
    return out


def load_poll_observations(path: str | Path) -> list[PollObservation]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"dataset OOS inexistente: {p}")
    with p.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"dataset OOS vacío: {p}")
    cols = set(rows[0])
    if CANONICAL.issubset(cols):
        return _canonical(rows, p.with_name("resultados_oficiales_2004_2023.csv"))
    if LEGACY.issubset(cols):
        return _legacy(rows)
    raise ValueError(f"unsupported OOS schema: {sorted(cols)}")


def _election_order(rows: list[PollObservation]) -> list[str]:
    return sorted(
        {r.election for r in rows},
        key=lambda election: date.fromisoformat(ELECTION_DATES.get(election, next(
            r.election_date for r in rows if r.election == election
        ))),
    )


def _bias_observations(rows: list[PollObservation]) -> list[Observation]:
    return [
        Observation(r.election, r.party, r.poll, r.actual, r.house, r.field_end)
        for r in rows
    ]


def _mae(predictions: list[float], actuals: list[float]) -> float:
    return sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(actuals)


def _predict_bias(name: str, train: list[Observation], obs: Observation) -> float:
    if name == "BASE":
        return obs.poll
    if name == "BIAS_COMUN":
        from .bias_filter import additive_common
        return additive_common(train, obs)
    if name == "BIAS_PARTIDO_SHRINK":
        from .bias_filter import additive_party
        return additive_party(train, obs)
    raise ValueError(f"unknown bias correction: {name}")


def run_oos(rows: list[PollObservation]) -> dict:
    if len({r.election for r in rows}) < 2:
        raise ValueError("OOS requiere al menos dos elecciones")
    for row in rows:
        if row.election not in ELECTION_DATES:
            raise ValueError(f"unknown election in OOS: {row.election}")
        if row.election_date != ELECTION_DATES[row.election]:
            raise ValueError(f"election date mismatch for {row.election}: {row.election_date}")
        field_end = date.fromisoformat(row.field_end)
        election_date = date.fromisoformat(row.election_date)
        if field_end >= election_date:
            raise ValueError(f"future leakage detected: {row.poll_id}")

    elections = _election_order(rows)
    latest = elections[-1]
    training = [r for r in rows if r.election != latest]
    holdout = [r for r in rows if r.election == latest]
    if len({r.election for r in training}) < 2:
        raise ValueError("OOS requires at least two historical training elections before holdout")

    train_bias = _bias_observations(training)
    selected_bias = select_best(train_bias)
    selected_context = select(training)

    bias_predictions = [
        _predict_bias(selected_bias.name, train_bias, Observation(
            r.election, r.party, r.poll, r.actual, r.house, r.field_end
        ))
        for r in holdout
    ]
    context_predictions = [
        predict_context(selected_context, training, r) for r in holdout
    ]
    holdout_actuals = [r.actual for r in holdout]
    holdout_polls = [r.poll for r in holdout]

    return {
        "status": "PASS",
        "contract": "EXPANDING_WINDOW_NO_FUTURE_LEAKAGE",
        "n_rows": len(rows),
        "n_elections": len(elections),
        "training_elections": elections[:-1],
        "holdout_election": latest,
        "selected_bias_correction": selected_bias.name,
        "selected_context_correction": selected_context,
        "holdout_mae_base": _mae(holdout_polls, holdout_actuals),
        "holdout_mae_selected_bias": _mae(bias_predictions, holdout_actuals),
        "holdout_mae_selected_context": _mae(context_predictions, holdout_actuals),
        "holdout_rows": len(holdout),
    }
