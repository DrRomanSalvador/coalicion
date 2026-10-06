#!/usr/bin/env python3
"""Acquire and validate the complete 2023 Congress constituency matrix."""
from __future__ import annotations
import hashlib, json, re, ssl, time, unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
import certifi
import requests
import pandas as pd
from bs4 import BeautifulSoup

OFFICIAL_XLSX = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
SECONDARY_BASE = "https://datoelectoral.es/circunscripciones/"
SLUG_ALIASES = {
    "Valencia/València": "valencia-valencia",
    "Valencia": "valencia-valencia",
    "País Valencià": "valencia-valencia",
    "Balears, Illes": "balears-illes",
    "Illes Balears": "balears-illes",
    "Baleares": "balears-illes",
    "Castellón/Castelló": "castellon-castello",
    "Castellón": "castellon-castello",
    "Castelló": "castellon-castello",
    "Araba/Álava": "araba-alava",
    "Álava": "araba-alava",
    "Araba": "araba-alava",
    "A Coruña": "a-coruna",
    "La Coruña": "a-coruna",
    "Gipuzkoa": "gipuzkoa",
    "Guipúzcoa": "gipuzkoa",
    "Bizkaia": "bizkaia",
    "Vizcaya": "bizkaia",
    "Las Palmas": "las-palmas",
    "Santa Cruz de Tenerife": "santa-cruz-de-tenerife",
}
SLUGS = {"Madrid":37,"Barcelona":32,"Valencia/València":16,"Alicante/Alacant":12,"Sevilla":12,"Málaga":11,"Murcia":10,"Cádiz":9,"A Coruña":8,"Balears, Illes":8,"Bizkaia":8,"Las Palmas":8,"Asturias":7,"Granada":7,"Pontevedra":7,"Santa Cruz de Tenerife":7,"Zaragoza":7,"Almería":6,"Córdoba":6,"Gipuzkoa":6,"Girona":6,"Tarragona":6,"Toledo":6,"Badajoz":5,"Cantabria":5,"Castellón/Castelló":5,"Ciudad Real":5,"Huelva":5,"Jaén":5,"Navarra":5,"Valladolid":5,"Albacete":4,"Araba/Álava":4,"Burgos":4,"Cáceres":4,"La Rioja":4,"León":4,"Lleida":4,"Lugo":4,"Ourense":4,"Salamanca":4,"Ávila":3,"Cuenca":3,"Guadalajara":3,"Huesca":3,"Palencia":3,"Segovia":3,"Teruel":3,"Zamora":3,"Soria":2,"Ceuta":1,"Melilla":1}

def fetch(url, attempts=5):
    last = None
    for i in range(attempts):
        try:
            ctx = ssl.create_default_context(cafile=certifi.where())
            req = Request(url, headers={"User-Agent":"coalicion/2026 matrix-acquirer"})
            with urlopen(req, timeout=45, context=ctx) as r:
                return r.read(), "CERTIFI_VALIDATED"
        except Exception as e:
            last = e
            time.sleep(min(2**i, 10))
    raise RuntimeError(f"download failed: {url}: {last}")

def normalize_label(name):
    """Normaliza únicamente la escritura de una etiqueta; no aproxima entidades."""
    x = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    x = re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().casefold()
    return re.sub(r"\s+", " ", x)

_NORMALIZED_ALIASES = {
    normalize_label(k): v for k, v in SLUG_ALIASES.items()
}

def slug(name):
    key = normalize_label(name)
    if key in _NORMALIZED_ALIASES:
        return _NORMALIZED_ALIASES[key]
    x = key.replace(" ", "-")
    return re.sub(r"[^a-z0-9-]+", "-", x).strip("-")

def parse_secondary(raw, province, seats):
    """Lee la tabla de candidaturas actual de Dato Electoral."""
    soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")
    for table in soup.find_all("table"):
        try:
            frames = pd.read_html(str(table))
        except (ValueError, ImportError):
            continue
        if not frames:
            continue
        df = frames[0]
        cols = [str(c).strip() for c in df.columns]
        if "Candidatura" not in cols or "Votos" not in cols:
            continue

        parties = {}
        blank = 0
        valid = None
        for _, row in df.iterrows():
            name = str(row.get("Candidatura", "")).strip()
            if not name or name == "Resultado":
                continue
            raw_votes = row.get("Votos")
            try:
                n = int(float(str(raw_votes).replace(".", "").replace(",", ".")))
            except (TypeError, ValueError):
                continue
            if name.casefold().startswith("votos en blanco"):
                blank = n
            elif name.casefold().startswith("total votos válidos"):
                valid = n
            else:
                parties[name] = n

        if not parties:
            continue
        if valid is None:
            valid = sum(parties.values()) + blank
        return {
            "seats": seats,
            "parties": parties,
            "blank_votes": blank,
            "valid_votes": valid,
            "source_url": SECONDARY_BASE + slug(province),
        }

    raise ValueError(f"candidate table missing or unreadable: {province}")

def build_from_official(raw, root):
    from src.data_pipeline import load_rows
    p = root/"artifacts/data/raw_2023_interior.xlsx"
    p.write_bytes(raw)
    rows = load_rows(p)
    matrix = {}
    for row in rows:
        c = row["province"]
        matrix.setdefault(c, {"seats":SLUGS.get(c),"parties":{},"blank_votes":0})
        matrix[c]["parties"][row["party"]] = row["votes"]
    return matrix

def validate(matrix, national):
    errors = []
    if set(matrix) != set(SLUGS): errors.append(f"circunscripciones: {len(matrix)}/52")
    if sum(x.get("seats") or 0 for x in matrix.values()) != 350: errors.append("escaños != 350")
    for c,x in matrix.items():
        if x.get("seats") != SLUGS.get(c): errors.append(f"escaños incorrectos: {c}")
        if any(not isinstance(v,int) or v < 0 for v in x["parties"].values()): errors.append(f"votos inválidos: {c}")
    candidate_total = sum(sum(x["parties"].values()) for x in matrix.values())
    if candidate_total != national["candidate_ballots"]: errors.append(f"total candidaturas {candidate_total} != {national['candidate_ballots']}")
    return {"valid":not errors,"errors":errors,"circunscripciones":len(matrix),"escaños":sum(x.get("seats") or 0 for x in matrix.values()),"candidate_votes_total":candidate_total}

def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root/"artifacts/data"; data_dir.mkdir(parents=True,exist_ok=True)
    national = json.loads((data_dir/"election_2023_national.json").read_text(encoding="utf-8"))
    events=[]; matrix=None
    try:
        raw,method=fetch(OFFICIAL_XLSX)
        digest=hashlib.sha256(raw).hexdigest()
        matrix=build_from_official(raw,root)
        validation=validate(matrix,national)
        events.append({"source":"MINISTERIO_DEL_INTERIOR","status":"DOWNLOADED_AND_PARSED","method":method,"sha256":digest,"validation":validation})
        if not validation["valid"]: raise RuntimeError("OFFICIAL_MATRIX_VALIDATION_FAILED")
        tier="OFFICIAL_PRIMARY"
    except Exception as e:
        events.append({"source":"MINISTERIO_DEL_INTERIOR","status":"FAILED","error":str(e)})
        matrix={}
        for province,seats in SLUGS.items():
            raw,_=fetch(SECONDARY_BASE+slug(province),attempts=3)
            matrix[province]=parse_secondary(raw,province,seats)
        validation=validate(matrix,national)
        tier="SECONDARY_REPLICA_VERIFIED"
        events.append({"source":"DATO_ELECTORAL","status":"DOWNLOADED_AND_PARSED","validation":validation})
        if not validation["valid"]: raise SystemExit("MATRIX_VALIDATION_FAILED")
    canonical={"schema":"ELECTION_2023_CONSTITUENCY_MATRIX_V1","election":2023,"type":"general","source_tier":tier,"data":{"constituencies":dict(sorted(matrix.items()))},"validation":validation}
    (data_dir/"election_2023_canonical.json").write_text(json.dumps(canonical,ensure_ascii=False,indent=2),encoding="utf-8")
    (data_dir/"election_2023_matrix_acquisition.json").write_text(json.dumps({"status":"READY","events":events,"source_tier":tier,"sha256":events[-1].get("sha256")},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"READY","source_tier":tier,"circunscripciones":validation["circunscripciones"],"escaños":validation["escaños"]},ensure_ascii=False))

if __name__=="__main__": main()
