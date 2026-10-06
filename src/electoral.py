"""Motor electoral determinista y fail-closed para el Congreso de los Diputados.

Principios:
- aritmética exacta con Fraction;
- umbral del 3 % sobre votos válidos;
- D'Hondt por circunscripción;
- empate por votos totales;
- empate absoluto: nunca se decide implícitamente;
- Ceuta/Melilla: mayoría simple, no D'Hondt;
- datos incompletos: bloqueo explícito.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Allocation:
    seats: Dict[str, int]
    status: str
    tie: Tuple[str, ...] = ()


def _validate_votes(votes: Mapping[str, int], valid_votes: int) -> None:
    if not isinstance(votes, Mapping):
        raise TypeError("votes debe ser un mapping candidatura -> votos")
    if not votes:
        return
    if not isinstance(valid_votes, int) or isinstance(valid_votes, bool) or valid_votes <= 0:
        raise ValueError("valid_votes debe ser un entero > 0")
    names = list(votes)
    if any(not isinstance(p, str) or not p.strip() for p in names):
        raise ValueError("Los nombres de candidatura deben ser cadenas no vacías")
    if len(set(names)) != len(names):
        raise ValueError("No puede haber candidaturas duplicadas")
    if any(
        not isinstance(v, int) or isinstance(v, bool) or v < 0
        for v in votes.values()
    ):
        raise ValueError("Los votos deben ser enteros no negativos")
    if sum(votes.values()) != valid_votes:
        raise ValueError(
            "Los votos de candidaturas deben sumar exactamente los votos válidos; "
            "si faltan candidaturas/datos, la asignación se bloquea"
        )


def _eligible(votes: Mapping[str, int], valid_votes: int) -> Dict[str, int]:
    return {
        party: value
        for party, value in votes.items()
        if Fraction(value * 100, valid_votes) >= 3
    }


def dhondt(
    votes: Mapping[str, int],
    seats: int,
    valid_votes: int,
) -> Allocation:
    """Asigna escaños D'Hondt de forma exacta y determinista.

    No acepta datos parciales. Si existe un empate absoluto en el último
    cociente, devuelve un estado pendiente en lugar de inventar un sorteo.
    """
    if not isinstance(seats, int) or isinstance(seats, bool) or seats < 1:
        raise ValueError("seats debe ser un entero >= 1")
    _validate_votes(votes, valid_votes)

    if not votes:
        return Allocation({}, "INSUFICIENTES_CANDIDATURAS")

    eligible = _eligible(votes, valid_votes)
    if not eligible:
        return Allocation({p: 0 for p in votes}, "INSUFICIENTES_CANDIDATURAS")

    quotients = [
        (Fraction(value, divisor), value, party, divisor)
        for party, value in eligible.items()
        for divisor in range(1, seats + 1)
    ]
    # La ley solo permite desempatar un cociente idéntico por votos totales.
    # El nombre/orden del diccionario jamás puede decidir un empate.
    quotients.sort(key=lambda item: (item[0], item[1]), reverse=True)

    if len(quotients) < seats:
        return Allocation({p: 0 for p in votes}, "INSUFICIENTES_CANDIDATURAS")

    selected = quotients[:seats]
    boundary_q, boundary_votes, _, _ = selected[-1]

    tied_at_boundary = [
        q for q in quotients
        if q[0] == boundary_q
    ]
    selected_at_boundary = [
        q for q in selected
        if q[0] == boundary_q
    ]

    if len(tied_at_boundary) > len(selected_at_boundary):
        tied_same_total_votes = tuple(
            sorted({q[2] for q in tied_at_boundary if q[1] == boundary_votes})
        )
        if len(tied_same_total_votes) >= 2:
            return Allocation(
                {p: 0 for p in votes},
                "EMPATE_ABSOLUTO_PENDIENTE",
                tied_same_total_votes,
            )

    out = {p: 0 for p in votes}
    for _, _, party, _ in selected:
        out[party] += 1

    if sum(out.values()) != seats:
        raise AssertionError("Invariante rota: no se han conservado los escaños")
    return Allocation(out, "OK")


def ceuta_melilla(votes: Mapping[str, int], valid_votes: Optional[int] = None) -> Allocation:
    """Adjudica el único escaño a la candidatura más votada.

    Si se suministra valid_votes, se valida además la integridad de los votos.
    """
    if not votes:
        raise ValueError("Se requiere al menos una candidatura")
    if valid_votes is not None:
        _validate_votes(votes, valid_votes)
    elif any(
        not isinstance(v, int) or isinstance(v, bool) or v < 0
        for v in votes.values()
    ):
        raise ValueError("Los votos deben ser enteros no negativos")

    maximum = max(votes.values())
    winners = tuple(sorted(p for p, v in votes.items() if v == maximum))
    if len(winners) > 1:
        return Allocation(
            {p: 0 for p in votes},
            "EMPATE_MAYORIA_PENDIENTE",
            winners,
        )
    return Allocation({p: int(p == winners[0]) for p in votes}, "OK")


def allocate(
    votes: Mapping[str, int],
    seats: int,
    valid_votes: int,
    special: str = "",
) -> Allocation:
    if special in {"Ceuta", "Melilla"}:
        if seats != 1:
            raise ValueError("Ceuta/Melilla deben tener exactamente 1 diputado")
        return ceuta_melilla(votes, valid_votes)
    return dhondt(votes, seats, valid_votes)


def merge_candidacies(*matrices: Mapping[str, int]) -> Dict[str, int]:
    """Fusiona votos antes de aplicar la ley electoral."""
    out: Dict[str, int] = {}
    for matrix in matrices:
        if not isinstance(matrix, Mapping):
            raise TypeError("Cada matriz debe ser un mapping")
        for party, votes in matrix.items():
            if not isinstance(votes, int) or isinstance(votes, bool) or votes < 0:
                raise ValueError("Los votos a fusionar deben ser enteros no negativos")
            out[party] = out.get(party, 0) + votes
    return out
