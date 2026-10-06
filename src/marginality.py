"""Margen electoral: votos necesarios para cambiar el último escaño bajo D'Hondt."""
from __future__ import annotations
from fractions import Fraction
from .electoral import allocate

def marginal_seat(votes, seats, blank_votes=0, special=""):
    valid=sum(votes.values())+blank_votes
    base=allocate(votes,seats,valid,special,blank_votes)
    if base.status!="OK":
        raise RuntimeError(base.status)
    if special in {"Ceuta","Melilla"}:
        ordered=sorted(votes.items(), key=lambda x:(x[1],x[0]), reverse=True)
        if len(ordered)<2: return None
        winner,runner=ordered[0],ordered[1]
        return {"winner":winner[0],"challenger":runner[0],"votes_to_change":max(0,runner[1]-winner[1]+1)}
    awarded=[]
    for party,n in base.seats.items():
        if n:
            awarded.append((Fraction(votes[party], n),party))
    if not awarded: return None
    last_party=min(awarded)[1]
    last_q=Fraction(votes[last_party], base.seats[last_party])
    challengers=[]
    for party,v in votes.items():
        if party==last_party or v==0: continue
        # Smallest integer x such that v/(current_seats+1) beats the last awarded quotient.
        needed=int(last_q*(base.seats.get(party,0)+1))+1-v
        challengers.append((max(0,needed),party))
    needed, challenger=min(challengers) if challengers else (None,None)
    return {"last_seat_holder":last_party,"challenger":challenger,"votes_to_change":needed,"last_quotient":last_q}
