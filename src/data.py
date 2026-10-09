"""Canonical data boundary for official Spanish election workbooks."""
from __future__ import annotations
import re, ssl, urllib.request
from pathlib import Path
import json, hashlib
from datetime import datetime, timezone
from typing import Any
import certifi, openpyxl
from .electoral import allocate

OFFICIAL_URL = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
CONSTITUENCY_HEADER = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*$")
CANDIDATE_VOTES = re.compile(r"^Votos\s*\((.*)\)\s*$")
CANDIDATE_SEATS = re.compile(r"^Escaños\s*\((.*)\)\s*$")

def download_workbook(destination: str | Path, manifest: str | Path | None = None) -> Path:
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
    context=ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(OFFICIAL_URL,context=context,timeout=60) as r:
        payload=r.read(); content_type=r.headers.get("Content-Type","")
    dest.write_bytes(payload)
    if not payload: raise RuntimeError("BLOCKED: official Interior dataset is empty")
    if manifest is not None:
        m=Path(manifest); m.parent.mkdir(parents=True,exist_ok=True)
        m.write_text(json.dumps({"schema":"OFFICIAL_SOURCE_MATERIALIZATION_V1","provider":"Ministerio del Interior","source_url":OFFICIAL_URL,"retrieved_at":datetime.now(timezone.utc).isoformat(),"content_type":content_type,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),"hash_scope":"workbook_bytes","path":str(dest)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return dest

def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())

def inspect_workbook(path: str | Path) -> dict[str,list[str]]:
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True); out={}
    for ws in wb.worksheets:
        rows=ws.iter_rows(min_row=1,max_row=min(ws.max_row,5),values_only=True)
        headers=next(iter(rows),()); out[ws.title]=[str(x) for x in headers if x is not None]
    return out

def _find_col(headers,*names):
    normalized={_norm(h):i for i,h in enumerate(headers)}
    for name in names:
        n=_norm(name)
        if n in normalized: return normalized[n]
    for i,h in enumerate(headers):
        n=_norm(h)
        if any(x in n for x in map(_norm,names)): return i
    return None

def _official_header(ws) -> list[Any]:
    for row in ws.iter_rows(min_row=1,max_row=min(ws.max_row,12),values_only=True):
        values=list(row)
        if any(isinstance(v,str) and v.strip().startswith("1 - ") for v in values): return values
    raise RuntimeError("BLOCKED: official Congress workbook header not found")

def _constituency_columns(headers:list[Any]) -> dict[int,str]:
    out={}; seen_codes=set()
    for index,value in enumerate(headers):
        if not isinstance(value,str): continue
        match=CONSTITUENCY_HEADER.match(value)
        if match:
            code=int(match.group(1))
            if 1<=code<=52:
                if code in seen_codes: raise ValueError(f"duplicated constituency code: {code}")
                seen_codes.add(code); out[index]=match.group(2).strip()
    if len(out)!=52 or seen_codes!=set(range(1,53)):
        raise ValueError(f"official workbook must expose exactly 52 constituencies; got {len(out)}")
    return out

def _integer(value:Any,context:str)->int:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not float(value).is_integer(): raise ValueError(f"{context}: non-integer numeric value")
    value=int(value)
    if value<0: raise ValueError(f"{context}: negative numeric value")
    return value

def available_elections(path:str|Path)->list[str]:
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True); dates=set()
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            if row and row[0] is not None and hasattr(row[0],"date"): dates.add(row[0].date().isoformat())
    return sorted(dates)

def load_official_constituency_matrix(path:str|Path,election_date:str|None=None)->dict[str,Any]:
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
    selected=election_date; election_rows=[]; constituency_cols=None
    for ws in wb.worksheets:
        headers=_official_header(ws); cols=_constituency_columns(headers); constituency_cols=cols
        for row_number,row in enumerate(ws.iter_rows(min_row=5,values_only=True),start=5):
            if not row or row[0] is None: continue
            raw_date=row[0]
            if not hasattr(raw_date,"date"): raise ValueError(f"{ws.title}:{row_number}: invalid election date")
            current_date=raw_date.date().isoformat()
            if selected is None: selected=current_date
            if current_date==selected: election_rows.append((raw_date,list(row)))
    if constituency_cols is None or selected is None: raise RuntimeError("BLOCKED: no official Congress election rows found")
    if not election_rows: raise ValueError(f"election date not found in official workbook: {selected}")
    parties={c:{} for c in constituency_cols.values()}; observed_seats={c:{} for c in constituency_cols.values()}; blanks={}; valid={}; seats={c:0 for c in constituency_cols.values()}; electors={}
    for _,row in election_rows:
        description=str(row[3] or "").strip(); votes_match=CANDIDATE_VOTES.match(description); seats_match=CANDIDATE_SEATS.match(description)
        for index,constituency in constituency_cols.items():
            if index>=len(row) or row[index] is None: continue
            value=_integer(row[index],f"{selected}:{description}:{constituency}")
            if votes_match:
                subject=votes_match.group(1).strip(); parties[constituency][subject]=parties[constituency].get(subject,0)+value
            elif seats_match:
                subject=seats_match.group(1).strip(); observed_seats[constituency][subject]=observed_seats[constituency].get(subject,0)+value; seats[constituency]+=value
            elif description=="Votos en blanco": blanks[constituency]=value
            elif description=="Votos válidos": valid[constituency]=value
            elif description=="Electores": electors[constituency]=value
    if len(parties)!=52 or set(parties)!=set(constituency_cols.values()): raise ValueError("official matrix lost constituency")
    if any(c not in blanks or c not in valid for c in parties): raise ValueError("official matrix lacks blank/valid rows")
    if sum(seats.values())!=350: raise ValueError(f"official observed seats do not sum to 350: {sum(seats.values())}")
    seat_reconciliation=[]
    for constituency in parties:
        if sum(parties[constituency].values())+blanks[constituency]!=valid[constituency]: raise ValueError(f"{constituency}: candidate votes + blank votes != valid votes")
        special = constituency if constituency in {"Ceuta","Melilla"} else ""
        allocation=allocate(parties[constituency],seats[constituency],valid[constituency],special,blanks[constituency])
        if allocation.status!="OK":
            raise ValueError(f"{constituency}: official D'Hondt allocation blocked: {allocation.status} {allocation.tie}")
        expected={p:n for p,n in allocation.seats.items() if n>0}
        observed={p:n for p,n in observed_seats[constituency].items() if n>0}
        if expected!=observed:
            missing=sorted(set(observed)-set(expected)); extra=sorted(set(expected)-set(observed))
            vote_seat_diff={p:{"observed":observed.get(p,0),"calculated":expected.get(p,0)} for p in sorted(set(observed)|set(expected)) if observed.get(p,0)!=expected.get(p,0)}
            raise ValueError(f"{constituency}: official vote-seat reconciliation failed; missing={missing}; extra={extra}; differences={vote_seat_diff}")
        seat_reconciliation.append({"constituency":constituency,"status":"PASS","observed_seat_winners":len(observed)})
    return {"election_date":selected,"constituencies":{c:{"seats":seats[c],"observed_seats":{p:s for p,s in sorted(observed_seats[c].items()) if s>0},"parties":dict(sorted(parties[c].items())),"blank_votes":blanks[c],"valid_votes":valid[c],"electors":electors.get(c)} for c in sorted(parties)},"validation":{"status":"PASS","circunscripciones":52,"escaños":sum(seats.values()),"candidate_votes_total":sum(sum(x.values()) for x in parties.values()),"blank_votes_total":sum(blanks.values()),"valid_votes_total":sum(valid.values()),"vote_seat_reconciliation":{"status":"PASS","constituencies":len(seat_reconciliation),"discrepancies":0,"method":"src.electoral.allocate","special_rules":["Ceuta","Melilla"]}}}

def load_rows(path:str|Path,election_date:str|None=None)->list[dict[str,Any]]:
    wb=openpyxl.load_workbook(path,read_only=True,data_only=True); rows_out=[]; seen=set()
    for ws in wb.worksheets:
        it=ws.iter_rows(values_only=True); headers=list(next(it,()))
        if not headers: continue
        pcol=_find_col(headers,"Provincia","Circunscripción","Province"); partycol=_find_col(headers,"Candidatura","Candidaturas","Partido","Siglas"); votescol=_find_col(headers,"Votos","Votos candidatura","Candidature votes")
        if pcol is None or partycol is None or votescol is None: continue
        for row_number,row in enumerate(it,start=2):
            if len(row)<=max(pcol,partycol,votescol): raise ValueError(f"fila truncada en {ws.title}:{row_number}")
            province,party,votes=row[pcol],row[partycol],row[votescol]
            if province in (None,"") or party in (None,""): raise ValueError(f"clave vacía en {ws.title}:{row_number}")
            value=_integer(votes,f"{ws.title}:{row_number}"); key=(str(province).strip(),str(party).strip())
            if key in seen: raise ValueError(f"duplicado candidatura×circunscripción: {key}")
            seen.add(key); rows_out.append({"sheet":ws.title,"province":key[0],"party":key[1],"votes":value})
    if rows_out:
        if len({r["province"] for r in rows_out})!=52: raise ValueError("se requieren exactamente 52 circunscripciones")
        return rows_out
    dates=available_elections(path); selected=election_date or (dates[-1] if dates else None)
    matrix=load_official_constituency_matrix(path,selected)
    for constituency,item in matrix["constituencies"].items():
        for party,votes in item["parties"].items():
            rows_out.append({"sheet":"Congreso","province":constituency,"party":party,"votes":votes,"election_date":selected})
    return rows_out

def write_json(rows:list[dict[str,Any]],destination:str|Path)->Path:
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8"); return dest



# Current survey registry normalization remains at the data boundary.
REQUIRED_SURVEY_FIELDS = ("id", "pollster", "publication_date", "shares", "evidence_level", "source_url")
SURVEY_PARTIES = ("PP", "PSOE", "Vox", "Sumar")

def _survey_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

def normalize_registry(source: str | Path, *, official: bool = False) -> dict[str, Any]:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("surveys"), list):
        raise ValueError("BLOCKED: invalid survey registry")
    rows = []
    for raw in data["surveys"]:
        if not isinstance(raw, dict) or any(not raw.get(k) for k in REQUIRED_SURVEY_FIELDS):
            raise ValueError("BLOCKED: survey missing required provenance")
        shares = raw["shares"]
        if not isinstance(shares, dict) or any(p not in shares for p in SURVEY_PARTIES):
            raise ValueError("BLOCKED: incomplete party share vector")
        if official and raw.get("evidence_level") != "PRIMARY_VERIFIED":
            raise ValueError("BLOCKED: official mode requires PRIMARY_VERIFIED evidence")
        rows.append({
            "id": str(raw["id"]),
            "pollster": str(raw["pollster"]),
            "publication_date": str(raw["publication_date"]),
            "field_start": raw.get("field_start"),
            "field_end": raw.get("field_end"),
            "sample_size": raw.get("sample_size"),
            "methodology": raw.get("methodology"),
            "shares": {p: float(shares[p]) for p in SURVEY_PARTIES},
            "evidence_level": str(raw["evidence_level"]),
            "source_url": str(raw["source_url"]),
        })
    return {
        "schema": "NORMALIZED_CURRENT_SURVEYS_V1",
        "as_of": data.get("as_of"),
        "count": len(rows),
        "surveys": rows,
        "source_registry_hash": _survey_hash(data),
        "normalized_hash": _survey_hash(rows),
        "official": official,
        "fail_closed": True,
    }
