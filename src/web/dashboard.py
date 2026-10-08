"""Politician-facing COALICIÓN situation room.

Presentation only: all substantive claims come from the canonical situation
state or already-materialized evidence. No national-to-territorial inference.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "artifacts/situation_state.json"
SURVEYS = ROOT / "data/surveys/current_2026/current_national.json"
PREDICTION = ROOT / "artifacts/territorial_prediction_20261008.json"
MASTER = ROOT / "ci_evidence/master_certification.json"
SOURCES = ROOT / "ci_evidence/poll_source_coverage.json"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def surveys() -> list[dict]:
    data = load_json(SURVEYS)
    return [x for x in data.get("surveys", []) if isinstance(x, dict)]


def csv_bytes(rows: list[dict]) -> bytes:
    keys = ["pollster", "publication_date", "field_start", "field_end",
            "sample_size", "evidence_level", "source_url"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


st.set_page_config(page_title="COALICIÓN · Situation Room", layout="wide")
st.title("COALICIÓN")
st.caption("Situation Room · evidencia materializada · fail-closed")

state = load_json(STATE)
rows = surveys()
pred = load_json(PREDICTION)
master = load_json(MASTER)
sources = load_json(SOURCES)

if not state:
    st.error("BLOCKED: no hay estado de situación materializado.")
    st.stop()

radar = state.get("radar", "UNKNOWN")
st.subheader("HOY")
st.metric("Radar", radar)
c1, c2, c3 = st.columns(3)
c1.metric("Cambios mostrados", len(state.get("headline", {}).get("changed", [])))
c2.metric("Preguntas", len(state.get("headline", {}).get("questions", [])))
c3.metric("Incertidumbres", len(state.get("headline", {}).get("uncertainties", [])))

tab1, tab2, tab3, tab4 = st.tabs(["Situación", "Electoral", "Territorio", "Evidencia"])

with tab1:
    st.subheader("Lo que cambió")
    changed = state.get("headline", {}).get("changed", [])
    if changed:
        for item in changed:
            st.markdown(f"**{item.get('party', item.get('code', 'Cambio'))}**")
            st.write(item.get("summary") or item.get("statement") or item.get("delta_pp"))
            if item.get("evidence"):
                st.caption("Evidencia: " + " · ".join(str(x) for x in item["evidence"] if x))
    else:
        st.info("No hay cambio electoral materializado que pueda afirmarse en este corte.")

    st.subheader("Preguntas de hoy")
    for item in state.get("headline", {}).get("questions", []):
        st.markdown(f"- {item.get('question')}")

    st.subheader("Lo que todavía no sabemos")
    for item in state.get("headline", {}).get("uncertainties", []):
        st.warning(item.get("statement"))

with tab2:
    st.subheader("Encuestas materializadas")
    if rows:
        view = []
        for p in rows:
            shares = p.get("shares", {})
            view.append({
                "Encuestadora": p.get("pollster"),
                "Publicación": p.get("publication_date"),
                "Campo": f"{p.get('field_start') or '—'} → {p.get('field_end') or '—'}",
                "Muestra": p.get("sample_size") or "—",
                "PP": shares.get("PP", "—"),
                "PSOE": shares.get("PSOE", "—"),
                "Vox": shares.get("Vox", "—"),
                "Sumar": shares.get("Sumar", "—"),
                "Evidencia": p.get("evidence_level", "—"),
            })
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("CSV", csv_bytes(rows), "encuestas_actuales.csv", "text/csv")
    else:
        st.warning("NO DISPONIBLE: no hay encuestas materializadas.")

with tab3:
    st.subheader("Territorio")
    if int(state.get("counts", {}).get("territorial_polls", 0) or 0) == 0:
        st.error("NO DISPONIBLE: no existen observaciones territoriales 2026 materializadas.")
    elif pred:
        st.json({
            "status": pred.get("status"),
            "observed_territorial_polls": pred.get("observed_territorial_polls"),
            "model": pred.get("model"),
            "calibration": pred.get("calibration"),
            "constituencies": pred.get("constituencies"),
        })

with tab4:
    st.subheader("Evidencia y límites")
    st.write("Estado de fuentes:", sources.get("status", "NO DISPONIBLE"))
    st.write("Certificación interna:", master.get("status", "NO DISPONIBLE"))
    st.write("Hash del estado:", state.get("state_hash", "NO DISPONIBLE"))
    st.caption(
        "COALICIÓN separa hechos, cambios, preguntas e incertidumbres. "
        "La ausencia de evidencia suficiente bloquea la afirmación correspondiente."
    )
