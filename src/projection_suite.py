"""Suite reproducible de proyección, incertidumbre y backtesting.
No inventa territorialidad: recibe una matriz territorial explícita.
"""
from __future__ import annotations
from dataclasses import asdict
from typing import Mapping, Sequence
import math
from .electoral import allocate
from .prediction import apply_share_swing
from .uncertainty import SimulationConfig, run_monte_carlo


def _national_votes(votes: Mapping[str, Mapping[str, int]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in votes.values():
        for party, value in row.items():
            out[party] = out.get(party, 0) + int(value)
    return out


def _allocate(votes, seats, blank, special):
    valid = sum(votes.values()) + blank
    result = allocate(votes, seats, valid, special, blank)
    if result.status != "OK":
        raise RuntimeError(result.status)
    return result


def project(votes_by_constituency, seats_by_constituency, blank_votes_by_constituency,
            share_changes=None, turnout_factors=None, special_by_constituency=None):
    """One deterministic projection with national, provincial, party, vote and seat views."""
    special_by_constituency = special_by_constituency or {}
    adjusted = apply_share_swing(
        votes_by_constituency,
        share_changes or {},
        turnout_factors or {},
    )
    seats: dict[str, dict[str, int]] = {}
    national_seats: dict[str, int] = {}
    for constituency, votes in adjusted.items():
        result = _allocate(
            votes, seats_by_constituency[constituency],
            blank_votes_by_constituency.get(constituency, 0),
            special_by_constituency.get(constituency, ""),
        )
        seats[constituency] = dict(result.seats)
        for party, value in result.seats.items():
            national_seats[party] = national_seats.get(party, 0) + value
    if sum(national_seats.values()) != sum(seats_by_constituency.values()):
        raise AssertionError("los escaños no conservan la magnitud electoral")
    national_votes = _national_votes(adjusted)
    party_valid_votes = sum(national_votes.values())
    shares = {p: v / party_valid_votes for p, v in national_votes.items()} if party_valid_votes else {}
    valid_including_blank = party_valid_votes + sum(blank_votes_by_constituency.values())
    return {
        "national": {"votes": national_votes, "vote_share": shares, "valid_votes_excluding_blank": party_valid_votes, "valid_votes_including_blank": valid_including_blank, "seats": national_seats},
        "provincial": seats,
        "party": {p: {"votes": national_votes.get(p, 0), "seats": national_seats.get(p, 0),
                      "vote_share": shares.get(p, 0.0)}
                  for p in sorted(set(national_votes) | set(national_seats))},
        "territorial_input": "EXPLICIT",
    }


def scenario_projection(base_votes, scenarios, seats_by_constituency, blank_votes_by_constituency,
                        special_by_constituency=None):
    """Catalog of explicit scenarios; each result is independently reproducible."""
    out = {}
    for name, changes, turnout in scenarios:
        out[name] = project(
            base_votes, seats_by_constituency, blank_votes_by_constituency,
            changes, turnout, special_by_constituency,
        )
    return out


def compare_projections(reference, candidate):
    parties = sorted(set(reference["party"]) | set(candidate["party"]))
    return {
        p: {
            "vote_change": candidate["party"].get(p, {}).get("votes", 0)
                         - reference["party"].get(p, {}).get("votes", 0),
            "seat_change": candidate["party"].get(p, {}).get("seats", 0)
                         - reference["party"].get(p, {}).get("seats", 0),
            "share_change": candidate["party"].get(p, {}).get("vote_share", 0.0)
                           - reference["party"].get(p, {}).get("vote_share", 0.0),
        } for p in parties
    }


def uncertainty_summary(draw_results: Sequence[Mapping[str, int]], quantiles=(0.1, 0.5, 0.9)):
    if not draw_results:
        raise ValueError("se necesitan simulaciones")
    parties = sorted({p for row in draw_results for p in row})
    result = {}
    for party in parties:
        values = sorted(row.get(party, 0) for row in draw_results)
        item = {}
        for q in quantiles:
            if not 0 <= q <= 1:
                raise ValueError("cuantil inválido")
            pos = (len(values) - 1) * q
            lo, hi = math.floor(pos), math.ceil(pos)
            item[str(q)] = values[lo] if lo == hi else values[lo] + (values[hi] - values[lo]) * (pos - lo)
        item["mean"] = sum(values) / len(values)
        item["min"] = values[0]
        item["max"] = values[-1]
        result[party] = item
    return result


def monte_carlo(votes_by_constituency, seats_by_constituency, blank_votes_by_constituency,
                special_by_constituency, sampler, iterations=10000, seed=0):
    result = run_monte_carlo(
        sampler, seats_by_constituency, blank_votes_by_constituency,
        special_by_constituency, SimulationConfig(iterations=iterations, seed=seed),
    )
    return asdict(result)


def backtest_rows(predictions: Sequence[Mapping], actuals: Sequence[Mapping]):
    """Backtest agregado por elección, partido y territorio.
    Rows use election/party/constituency plus predicted and actual vote/seats fields.
    """
    if len(predictions) != len(actuals) or not predictions:
        raise ValueError("predicciones y resultados incompatibles")
    errors = []
    for pred, actual in zip(predictions, actuals):
        if any(pred.get(k) != actual.get(k) for k in ("election", "party", "constituency")):
            raise ValueError("filas desalineadas")
        vote_error = float(pred.get("votes", 0)) - float(actual.get("votes", 0))
        seat_error = float(pred.get("seats", 0)) - float(actual.get("seats", 0))
        errors.append({**{k: pred.get(k) for k in ("election", "party", "constituency")},
                       "vote_error": vote_error, "seat_error": seat_error})
    def mae(key):
        return sum(abs(x[key]) for x in errors) / len(errors)
    elections = sorted({x["election"] for x in errors})
    parties = sorted({x["party"] for x in errors})
    constituencies = sorted({x["constituency"] for x in errors})
    def aggregate(field, values):
        return {"n": len(values), "mae": sum(abs(v[field]) for v in values) / len(values),
                "bias": sum(v[field] for v in values) / len(values)}
    return {
        "status": "PASS",
        "overall": {"vote": aggregate("vote_error", errors), "seat": aggregate("seat_error", errors)},
        "by_election": {e: aggregate("vote_error", [x for x in errors if x["election"] == e]) for e in elections},
        "by_party": {p: aggregate("vote_error", [x for x in errors if x["party"] == p]) for p in parties},
        "by_constituency": {c: aggregate("vote_error", [x for x in errors if x["constituency"] == c]) for c in constituencies},
        "seat_by_election": {e: aggregate("seat_error", [x for x in errors if x["election"] == e]) for e in elections},
        "seat_mae": mae("seat_error"),
        "vote_mae": mae("vote_error"),
        "rows": len(errors),
    }
