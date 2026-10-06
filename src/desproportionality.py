"""LSQ descriptivo; no altera votos ni escaños."""
import math
def loose_lsq(vote_shares, seat_shares):
    if len(vote_shares)!=len(seat_shares) or not vote_shares: raise ValueError("dimensiones inválidas")
    return math.sqrt(0.5*sum((float(v)-float(s))**2 for v,s in zip(vote_shares,seat_shares)))
def index_from_counts(votes,seats):
    tv,ts=sum(votes),sum(seats)
    if tv<=0 or ts<=0: raise ValueError("totales inválidos")
    return loose_lsq([v/tv for v in votes],[s/ts for s in seats])
