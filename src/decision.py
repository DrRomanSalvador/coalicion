"""Canonical decision orchestration: explicit, auditable electoral scenarios."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Mapping
import hashlib, json
from .electoral import allocate
from .coalition import coalition_decision

@dataclass(frozen=True)
class Scenario:
    scenario_type: str
    party: str | None = None
    shift_type: str | None = None
    shift_value: float | None = None
    territorial_distribution: str = "user_defined"
    assumptions: tuple[str, ...] = ()
    source: str = "user_defined"
    uncertainty: str = "none"

def sha256_json(obj) -> str:
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def validate_scenario(s: Scenario) -> None:
    if s.scenario_type not in {"coalition","national_shift","territorial_shift"}:
        raise ValueError("scenario_type inválido")
    if s.scenario_type != "coalition" and s.shift_value is None:
        raise ValueError("shift_value obligatorio")
    if s.scenario_type == "national_shift" and s.territorial_distribution == "unspecified":
        raise ValueError("AMBIGUOUS_SCENARIO")

def coalition_result(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    valid_votes: Mapping[str, int],
    coalition: tuple[str, ...],
    special: Mapping[str, str] | None = None,
    blank: Mapping[str, int] | None = None,
) -> dict:
    """Delegate coalition allocation to the single canonical coalition engine."""
    blank = blank or {}
    special = special or {}
    if set(votes_by_constituency) != set(seats_by_constituency) or set(votes_by_constituency) != set(valid_votes):
        raise ValueError("circunscripciones incompatibles")
    for c, row in votes_by_constituency.items():
        expected = sum(row.values()) + blank.get(c, 0)
        if expected != valid_votes[c]:
            raise ValueError(f"{c}: votos válidos inconsistentes")
    result = coalition_decision(
        votes_by_constituency,
        seats_by_constituency,
        blank,
        coalition,
        special,
    )
    return {
        "scenario": asdict(Scenario(
            "coalition",
            territorial_distribution="sum_by_province",
            assumptions=("no vote transfer", "same turnout"),
            source="input_dataset",
        )),
        "coalition": "+".join(coalition),
        "separate_seats_by_constituency": {
            item["constituency"]: item["separate"] for item in result["all_constituencies"]
        },
        "coalition_seats_by_constituency": {
            item["constituency"]: item["coalition"] for item in result["all_constituencies"]
        },
        "delta_by_constituency": {
            item["constituency"]: item["delta"] for item in result["all_constituencies"]
        },
        "total_separate": result["separate_seats"],
        "total_coalition": result["coalition_seats"],
        "delta": result["benefit"],
        "changed_constituencies": result["decisive_constituencies"],
        "certificate_input_hash": sha256_json(votes_by_constituency),
        "canonical_engine": "src.coalition",
    }

def apply_absolute_shift(votes_by_constituency, party, shift_points: float, territorial_distribution: str) -> dict:
    """Transfer percentage points between existing candidatures, preserving vote mass.

    A positive shock gives the target party a share of the existing valid vote
    total and removes exactly that mass from the other candidatures. A negative
    shock performs the inverse transfer. Integer votes are allocated by largest
    remainder with party-name tie ordering, so the transformation is exact and
    reproducible.
    """
    if territorial_distribution == "unspecified":
        raise ValueError("AMBIGUOUS_SCENARIO")
    if territorial_distribution != "uniform_by_province":
        raise ValueError("Solo uniform_by_province está implementado")
    shift = Fraction(str(shift_points))
    if not shift:
        return {c: dict(row) for c, row in votes_by_constituency.items()}
    if not -100 < shift < 100:
        raise ValueError("El shock debe estar estrictamente entre -100 y 100 puntos")
    out = {}
    for c, row0 in votes_by_constituency.items():
        row = dict(row0)
        if party not in row:
            raise ValueError(f"{c}: candidatura ausente")
        total = sum(row.values())
        if total <= 0:
            raise ValueError(f"{c}: masa electoral no positiva")
        if shift > 0:
            transfer = shift * total / 100
            max_transfer = total - row[party]
            if transfer > max_transfer:
                raise ValueError(f"{c}: shock positivo superior a los votos transferibles")
            source = {p: v for p, v in row.items() if p != party and v > 0}
            target = party
            sign = 1
        else:
            transfer = -shift * total / 100
            if transfer > row[party]:
                raise ValueError(f"{c}: shock negativo superior a los votos de {party}")
            source = {party: row[party]}
            target = None
            sign = -1
        if transfer.denominator != 1:
            raise ValueError(f"{c}: el shock produce una transferencia fraccionaria; defina un redondeo explícito")
        amount = int(transfer)
        if amount == 0:
            out[c] = row
            continue
        def distribute(pool, amount):
            pool_total = sum(pool.values())
            if pool_total < amount:
                raise ValueError(f"{c}: masa transferible insuficiente")
            base = {}
            remainders = []
            assigned = 0
            for p, votes in sorted(pool.items()):
                q = Fraction(amount * votes, pool_total)
                n = q.numerator // q.denominator
                base[p] = n
                assigned += n
                remainders.append((q - n, p))
            for _, p in sorted(remainders, key=lambda x: (-x[0], x[1]))[:amount - assigned]:
                base[p] += 1
            return base
        if sign == 1:
            cuts = distribute(source, amount)
            for p, n in cuts.items():
                row[p] -= n
            row[party] += amount
        else:
            row[party] -= amount
            gains = {p: v for p, v in row.items() if p != party and v >= 0}
            adds = distribute(gains, amount)
            for p, n in adds.items():
                row[p] += n
        if sum(row.values()) != total or any(v < 0 for v in row.values()):
            raise AssertionError(f"{c}: el shock no conserva la masa electoral")
        out[c] = row
    return out

