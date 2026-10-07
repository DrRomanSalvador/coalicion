"""Centro de decisión rápida: encuesta → voto → territorio → escaños → marginalidad → pactos.

Contrato: todos los datos electorales territoriales deben ser explícitos. No rellena
faltantes ni convierte pesos de escenarios en probabilidades. Reutiliza los motores
canónicos y devuelve un snapshot determinista y trazable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence
import hashlib
import json

from .projection_suite import project, compare_projections, uncertainty_summary
from .marginality import rank_marginality
from .scenarios import compare_scenarios as compare_coalition_scenarios


VERSION = "1.0"
EXPECTED_CONSTITUENCIES = 52
EXPECTED_SEATS = 350


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _validate_matrix(votes, seats, blank):
    if not votes:
        raise ValueError("BLOCKED: matriz territorial vacía")
    missing = sorted(set(votes) - set(seats))
    extra_seats = sorted(set(seats) - set(votes))
    if missing or extra_seats:
        raise ValueError(f"BLOCKED: claves territoriales incompatibles; faltan={missing}; sobran_escaños={extra_seats}")
    extra_blank = sorted(set(blank) - set(votes))
    if extra_blank:
        raise ValueError(f"BLOCKED: votos en blanco para circunscripciones inexistentes: {extra_blank}")
    for constituency, row in votes.items():
        if not row or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in row.values()):
            raise ValueError(f"BLOCKED: votos inválidos en {constituency}")
        if not isinstance(seats[constituency], int) or isinstance(seats[constituency], bool) or seats[constituency] <= 0:
            raise ValueError(f"BLOCKED: magnitud inválida en {constituency}")
        if not isinstance(blank.get(constituency, 0), int) or isinstance(blank.get(constituency, 0), bool) or blank.get(constituency, 0) < 0:
            raise ValueError(f"BLOCKED: votos en blanco inválidos en {constituency}")


def _marginality_input(votes, seats, blank, special):
    return [
        {
            "name": constituency,
            "votes": dict(row),
            "seats": int(seats[constituency]),
            "blank_votes": int(blank.get(constituency, 0)),
            "special": special.get(constituency, ""),
        }
        for constituency, row in sorted(votes.items())
    ]


def _national_changes(reference, current):
    if reference is None:
        return []
    delta = compare_projections(reference, current)
    return sorted(
        [
            {"party": party, **values}
            for party, values in delta.items()
            if values["vote_change"] or values["seat_change"] or values["share_change"]
        ],
        key=lambda x: (-abs(x["seat_change"]), -abs(x["vote_change"]), x["party"]),
    )


def decision_snapshot(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    *,
    special_by_constituency: Mapping[str, str] | None = None,
    share_changes: Mapping | None = None,
    turnout_factors: Mapping | None = None,
    previous_projection: Mapping | None = None,
    uncertainty_draws: Sequence[Mapping[str, int]] | None = None,
    coalitions: Sequence[Sequence[str]] | None = None,
    poll_summary: Mapping | None = None,
    strict_territory: bool = True,
) -> dict:
    """Produce one actionable, reproducible decision snapshot.

    Coalition results are electoral counterfactuals only; no political feasibility
    or negotiation probability is inferred.
    """
    blank = dict(blank_votes_by_constituency or {})
    special = dict(special_by_constituency or {})
    _validate_matrix(votes_by_constituency, seats_by_constituency, blank)
    if strict_territory:
        if len(votes_by_constituency) != EXPECTED_CONSTITUENCIES:
            raise ValueError(
                f"BLOCKED: se esperan {EXPECTED_CONSTITUENCIES} circunscripciones; "
                f"recibidas {len(votes_by_constituency)}"
            )
        if sum(int(v) for v in seats_by_constituency.values()) != EXPECTED_SEATS:
            raise ValueError(
                f"BLOCKED: se esperan {EXPECTED_SEATS} escaños; "
                f"recibidos {sum(int(v) for v in seats_by_constituency.values())}"
            )

    projection = project(
        votes_by_constituency,
        seats_by_constituency,
        blank,
        share_changes,
        turnout_factors,
        special,
    )
    marginality = rank_marginality(
        _marginality_input(votes_by_constituency, seats_by_constituency, blank, special)
    )

    coalition_result = None
    if coalitions:
        normalized = [tuple(c) for c in coalitions]
        if any(len(c) < 2 or len(set(c)) != len(c) for c in normalized):
            raise ValueError("BLOCKED: coalición inválida")
        valid_votes = {
            c: sum(votes_by_constituency[c].values()) + blank.get(c, 0)
            for c in votes_by_constituency
        }
        coalition_result = compare_coalition_scenarios(
            votes_by_constituency,
            seats_by_constituency,
            valid_votes,
            blank,
            normalized,
            special,
        )

    uncertainty = None
    if uncertainty_draws is not None:
        uncertainty = uncertainty_summary(uncertainty_draws)

    changes = _national_changes(previous_projection, projection)
    payload = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "OK",
        "territory": {
            "constituencies": len(votes_by_constituency),
            "seats": sum(int(v) for v in seats_by_constituency.values()),
            "strict_52": strict_territory,
        },
        "polls": dict(poll_summary) if poll_summary is not None else None,
        "projection": projection,
        "marginality": {
            "count": len(marginality),
            "most_marginal": marginality[:10],
        },
        "coalitions": coalition_result,
        "uncertainty": uncertainty,
        "changes": changes,
        "traceability": {
            "input_hash": _hash({
                "votes": votes_by_constituency,
                "seats": seats_by_constituency,
                "blank": {k: int(blank.get(k, 0)) for k in sorted(votes_by_constituency)},
                "special": {k: special.get(k, "") for k in sorted(votes_by_constituency)},
                "share_changes": share_changes or {},
                "turnout_factors": turnout_factors or {},
                "coalitions": coalitions or [],
            }),
        },
        "limitations": [
            "La territorialización solo usa datos territoriales explícitos.",
            "Las coaliciones son contrafactuales electorales, no una predicción de pacto.",
            "La incertidumbre solo se muestra si existen simulaciones explícitas.",
        ],
    }
    stable_payload = dict(payload)
    stable_payload.pop("generated_at", None)
    payload["traceability"]["output_hash"] = _hash(stable_payload)
    return payload
