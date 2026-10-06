"""Certificado falsable del error de encuestas.

Principio: no promete predicción infalible. Las identidades matemáticas sí son exactas;
las inferencias se declaran falsables y solo se aceptan OOS.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Sequence
from .poll_error import PollObservation


@dataclass(frozen=True)
class ErrorDecomposition:
    """Descomposición exacta por observación.

    total_error = common_sector + house_residual + residual
    donde common_sector es la media de la elección y house_residual la desviación
    de la casa respecto a esa media. La identidad es algebraicamente exacta.
    """
    election: str
    party: str
    house: str
    total_error: float
    sector_error: float
    house_component: float
    residual: float


def decompose_sector_house(rows: Sequence[PollObservation]) -> list[ErrorDecomposition]:
    groups: dict[tuple[str, str], list[PollObservation]] = {}
    for r in rows:
        groups.setdefault((r.election, r.party), []).append(r)

    out = []
    for (election, party), group in sorted(groups.items()):
        sector = sum(r.error for r in group) / len(group)
        for r in group:
            house_component = r.error - sector
            out.append(ErrorDecomposition(
                election, party, r.house, r.error, sector,
                house_component, 0.0,
            ))
    return out


@dataclass(frozen=True)
class MovementDecomposition:
    election: str
    party: str
    previous_actual: float
    actual_change: float
    observed_change: float
    level_error: float
    movement_error: float


def decompose_movement(rows: Sequence[PollObservation]) -> list[MovementDecomposition]:
    """Separa error de nivel y error de movimiento entre elecciones comparables."""
    elections = sorted(
        {r.election for r in rows},
        key=lambda e: min(r.election_date for r in rows if r.election == e),
    )
    by_key: dict[tuple[str, str], PollObservation] = {}
    for r in rows:
        # Una sola observación por elección/partido: se exige previamente un
        # agregador documentado si hay varias casas.
        key = (r.election, r.party)
        if key in by_key:
            raise ValueError(
                "decompose_movement requiere una observación agregada por elección/partido"
            )
        by_key[key] = r

    out = []
    for i in range(1, len(elections)):
        prev, cur = elections[i - 1], elections[i]
        parties = sorted(
            {p for e, p in by_key if e == prev}
            & {p for e, p in by_key if e == cur}
        )
        for party in parties:
            old, new = by_key[(prev, party)], by_key[(cur, party)]
            actual_change = new.actual - old.actual
            observed_change = new.poll - old.actual
            out.append(MovementDecomposition(
                cur, party, old.actual, actual_change, observed_change,
                new.error, observed_change - actual_change,
            ))
    return out


@dataclass(frozen=True)
class FalsificationResult:
    claim: str
    status: str
    n: int
    mae: float
    rmse: float
    median_error: float
    max_abs_error: float


def falsification_metrics(rows: Sequence[PollObservation]) -> FalsificationResult:
    if not rows:
        raise ValueError("No hay observaciones")
    errors = [r.error for r in rows]
    return FalsificationResult(
        claim="La distribución observada del error es reproducible con los datos documentados",
        status="TESTABLE",
        n=len(errors),
        mae=sum(abs(x) for x in errors) / len(errors),
        rmse=sqrt(sum(x*x for x in errors) / len(errors)),
        median_error=median(errors),
        max_abs_error=max(abs(x) for x in errors),
    )


@dataclass(frozen=True)
class EvidenceCertificate:
    """Estado auditable de una afirmación.

    IDENTIFICABLE: hay evidencia suficiente para medir el efecto.
    NO_IDENTIFICABLE: el diseño no permite separar explicaciones.
    FALSABLE: existe prueba OOS predefinida.
    """
    claim: str
    status: str
    evidence: str
    falsification_test: str


def certificate_for_context(
    rows: Sequence[PollObservation],
    *,
    require_house: bool = True,
    require_government: bool = True,
) -> EvidenceCertificate:
    if not rows:
        return EvidenceCertificate(
            "Efecto contextual de encuesta",
            "NO_IDENTIFICABLE",
            "No existen observaciones documentadas",
            "Cargar datos fechados y repetir OOS",
        )
    missing = []
    if require_house and any(not r.house for r in rows):
        missing.append("house")
    if require_government and any(not r.governing_party for r in rows):
        missing.append("governing_party")
    if missing:
        return EvidenceCertificate(
            "Efecto contextual de encuesta",
            "NO_IDENTIFICABLE",
            "Faltan: " + ", ".join(missing),
            "Repetir el análisis tras completar los metadatos",
        )
    return EvidenceCertificate(
        "Efecto contextual de encuesta",
        "FALSABLE",
        "Casa y contexto de gobierno están documentados",
        "Leave-one-election-out; comparar BASE con modelos contextuales y exigir no degradación conjunta",
    )
