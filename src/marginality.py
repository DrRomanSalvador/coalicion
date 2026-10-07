"""Marginalidad D'Hondt: último cociente, primer perdedor y voto de desplazamiento."""
from __future__ import annotations
from fractions import Fraction
from .electoral import allocate


def marginal_seat(votes, seats, blank_votes=0, special=""):
    valid = sum(votes.values()) + blank_votes
    base = allocate(votes, seats, valid, special, blank_votes)
    if base.status != "OK":
        raise RuntimeError(base.status)

    if special in {"Ceuta", "Melilla"}:
        ordered = sorted(votes.items(), key=lambda x: (x[1], x[0]), reverse=True)
        if len(ordered) < 2:
            return None
        winner, runner = ordered[0], ordered[1]
        return {
            "winner": winner[0],
            "challenger": runner[0],
            "votes_to_change": max(0, runner[1] - winner[1] + 1),
            "winner_votes": winner[1],
            "challenger_votes": runner[1],
            "vote_margin": winner[1] - runner[1],
        }

    awarded = [
        (Fraction(votes[p], n), p)
        for p, n in base.seats.items() if n and votes.get(p, 0) >= 0
    ]
    if not awarded:
        return None

    last_q, last_party = min(awarded)
    challengers = []
    for party, v in votes.items():
        if party == last_party:
            continue
        current = base.seats.get(party, 0)
        needed = max(0, int(last_q * (current + 1)) + 1 - v)
        challengers.append((needed, party, Fraction(v, current + 1)))

    if not challengers:
        return None
    needed, challenger, challenger_q = min(challengers, key=lambda x: (x[0], x[1]))
    return {
        "last_seat_holder": last_party,
        "challenger": challenger,
        "votes_to_change": needed,
        "last_quotient": last_q,
        "challenger_next_quotient": challenger_q,
        "quotient_margin": last_q - challenger_q,
        "seat_margin": needed,
        "last_seat_votes": votes[last_party],
        "last_seat_count": base.seats[last_party],
    }


def rank_marginality(constituencies):
    """Rank constituency marginal seats by votes needed to change them.

    Input: iterable of dicts with name, votes, seats, blank_votes, optional special.
    """
    ranked=[]
    for item in constituencies:
        result=marginal_seat(item["votes"], item["seats"], item.get("blank_votes", 0), item.get("special", ""))
        if result is None:
            continue
        ranked.append({"constituency":item["name"], **result})
    return sorted(ranked, key=lambda x:(x["votes_to_change"], x["constituency"]))


def compare_marginality(snapshots):
    """Compare marginal-seat rankings across dated snapshots."""
    out=[]
    for snapshot in snapshots:
        ranked=rank_marginality(snapshot["constituencies"])
        out.append({"date":snapshot["date"],"ranking":ranked})
    return out
