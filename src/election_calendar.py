"""Deterministic election-calendar engine for the 2026 Spanish general election."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any

CONVOCATION_DATE = date(2026, 10, 5)
ELECTION_DATE = date(2026, 11, 29)
CAMPAIGN_START = date(2026, 11, 13)
CAMPAIGN_END = date(2026, 11, 27)

def _event(code: str, title: str, when: date, source: str, kind: str="legal") -> dict[str, Any]:
    return {"code": code, "title": title, "date": when.isoformat(), "source": source, "kind": kind}

def official_2026_timeline() -> list[dict[str, Any]]:
    source = "BOE-A-2026-20742 + LOREG"
    return sorted([
        _event("CONVOCATORIA", "Publicación de la convocatoria", CONVOCATION_DATE + timedelta(days=1), source),
        _event("COALICIONES", "Fin del plazo para comunicar coaliciones", CONVOCATION_DATE + timedelta(days=10), source),
        _event("CENSO_CONSULTA_INICIO", "Inicio del periodo de consulta del censo", CONVOCATION_DATE + timedelta(days=6), source),
        _event("CENSO_CONSULTA_FIN", "Fin del periodo de consulta del censo", CONVOCATION_DATE + timedelta(days=13), source),
        _event("CENSO_RECLAMACIONES", "Fin ordinario para reclamaciones al censo", CONVOCATION_DATE + timedelta(days=14), source),
        _event("CANDIDATURAS_INICIO", "Inicio de presentación de candidaturas", CONVOCATION_DATE + timedelta(days=15), source),
        _event("CANDIDATURAS_FIN", "Fin de presentación de candidaturas", CONVOCATION_DATE + timedelta(days=20), source),
        _event("CANDIDATURAS_PUBLICACION", "Publicación de candidaturas presentadas", CONVOCATION_DATE + timedelta(days=22), source),
        _event("IRREGULARIDADES", "Comunicación de irregularidades de candidaturas", CONVOCATION_DATE + timedelta(days=24), source),
        _event("SUBSANACION_FIN", "Fin del plazo de subsanación de candidaturas", CONVOCATION_DATE + timedelta(days=26), source),
        _event("PROCLAMACION", "Proclamación de candidaturas", CONVOCATION_DATE + timedelta(days=27), source),
        _event("PROCLAMACION_PUBLICACION", "Publicación de candidaturas proclamadas", CONVOCATION_DATE + timedelta(days=28), source),
        _event("CAMPAÑA_INICIO", "Inicio de campaña electoral", CAMPAIGN_START, source),
        _event("CAMPAÑA_FIN", "Fin de campaña electoral", CAMPAIGN_END, source),
        _event("ELECCION", "Jornada electoral", ELECTION_DATE, source),
        _event("CONSTITUCION", "Sesión constitutiva de las Cámaras", date(2026, 12, 23), source),
    ], key=lambda x: x["date"])

def timeline(as_of: date | None = None) -> list[dict[str, Any]]:
    as_of = as_of or date.today()
    out=[]
    for e in official_2026_timeline():
        d=date.fromisoformat(e["date"])
        x=dict(e); x["days_remaining"]=(d-as_of).days
        x["status"]="past" if d<as_of else "today" if d==as_of else "upcoming"
        out.append(x)
    return out

def critical_window(as_of: date | None = None, horizon_days: int=31) -> list[dict[str, Any]]:
    as_of=as_of or date.today()
    return [x for x in timeline(as_of) if -2 <= x["days_remaining"] <= horizon_days]
