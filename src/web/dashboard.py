"""Minimal politician-facing Streamlit dashboard for COALICIÓN.

The dashboard is a presentation layer over materialized evidence. It never
turns national polling into fake territorial observations.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SURVEYS = ROOT / "data/surveys/current_2026/current_national.json"
PREDICTION = ROOT / "artifacts/territorial_prediction_20261008.json"
OBSERVATIONS = ROOT / "artifacts/estimation/observations.json"
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


st.set_page_config(page_title="COALICIÓN — Sala de situación", layout="wide")
st.title("COALICIÓN")
st.caption("Sala de situación electoral reproducible · demo no oficial")

rows = surveys()
pred = load_json(PREDICTION)
master = load_json(MASTER)
sources = load_json(SOURCES)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Situación", "Encuestas", "Territorio", "Escaños", "Evidencia"]
)

with tab1:
    st.subheader("Situación actual")
    c1, c2, c3 = st.columns(3)
    c1.metric("Encuestas actuales", len(rows))
    c2.metric("Fuentes operativas", sources.get("operational", sources.get("ok", "—")))
    c3.metric("Estado interno", master.get("status", "NO DISPONIBLE"))
    st.info(
        "Los datos actuales pueden contener observaciones secundarias reconciliadas. "
        "La interfaz las identifica y no las presenta como evidencia primaria."
    )

with tab2:
    st.subheader("Últimas encuestas")
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
        st.download_button("Descargar CSV", csv_bytes(rows), "encuestas_actuales.csv", "text/csv")
    else:
        st.warning("NO DISPONIBLE: no hay encuestas materializadas.")

with tab3:
    st.subheader("Territorio")
    if pred:
        st.json({
            "status": pred.get("status"),
            "observed_territorial_polls": pred.get("observed_territorial_polls"),
            "model": pred.get("model"),
            "calibration": pred.get("calibration"),
            "constituencies": pred.get("constituencies"),
        })
    st.warning(
        "No se muestran encuestas territoriales 2026 inventadas. "
        "La predicción territorial solo puede publicarse cuando el contrato de evidencia lo permite."
    )

with tab4:
    st.subheader("Escaños")
    if str(pred.get("status", "")).upper() == "PASS":
        seats = pred.get("national_seats") or pred.get("seats")
        if seats:
            st.bar_chart(seats)
        else:
            st.warning("NO DISPONIBLE: predicción sin reparto de escaños materializado.")
    else:
        st.warning("NO DISPONIBLE: no existe una predicción territorial 2026 certificada.")

with tab5:
    st.subheader("Evidencia y límites")
    st.write("Certificación interna:", master.get("status", "NO DISPONIBLE"))
    st.write("Cobertura de fuentes:", sources.get("status", "NO DISPONIBLE"))
    st.write("Predicción demo:", pred.get("status", "NO MATERIALIZADA"))
    st.caption(
        "COALICIÓN es infraestructura neutral de auditoría y simulación. "
        "La ausencia de auditoría externa impide cualquier afirmación de validez oficial."
    )
