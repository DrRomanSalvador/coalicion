#!/usr/bin/env python3
"""Generate a descriptive 2023 coalition report; never recommends a coalition."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from src.neutral_coalition import enumerate_all_coalition_results

ROOT=Path(__file__).resolve().parents[1]
MATRIX=ROOT/"artifacts/data/election_2023_canonical.json"
ANCHOR=ROOT/"data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json"
OUT_JSON=ROOT/"artifacts/neutral_coalition_2023.json"
OUT_MD=ROOT/"reports/neutral_coalition_2023.md"

def sha256_json(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description="Análisis descriptivo neutral de coaliciones")
    ap.add_argument("--matrix",type=Path,default=MATRIX)
    ap.add_argument("--anchor",type=Path,default=ANCHOR)
    ap.add_argument("--parties",nargs="*")
    ap.add_argument("--min-size",type=int,default=2)
    ap.add_argument("--max-size",type=int)
    args=ap.parse_args()
    if not args.matrix.is_file(): raise SystemExit(f"BLOCKED: falta matriz canónica: {args.matrix}")
    matrix=json.loads(args.matrix.read_text(encoding="utf-8"))
    if matrix.get("source")!="INTERIOR_PRIMARY" or matrix.get("election")!="2023": raise SystemExit("BLOCKED: matriz primaria 2023 inválida")
    provinces=matrix.get("data",{}).get("provinces",[])
    if len(provinces)!=52 or sum(p.get("seats",0) for p in provinces)!=350: raise SystemExit("BLOCKED: matriz 2023 incompleta")
    votes={p["name"]:{r["name"]:r["votes"] for r in p["parties"]} for p in provinces}
    seats={p["name"]:p["seats"] for p in provinces}
    valid=matrix["data"]["valid_votes"]; blank=matrix["data"].get("blank_votes",{}); special=matrix["data"].get("special",{})
    anchor=json.loads(args.anchor.read_text(encoding="utf-8")) if args.anchor.is_file() else {}
    parties=tuple(args.parties or anchor.get("canonical_candidate_labels",[]))
    if len(parties)<2: raise SystemExit("BLOCKED: universo de candidaturas insuficiente")
    results=[]
    for r in enumerate_all_coalition_results(votes,seats,valid,parties,special,blank,args.min_size,args.max_size):
        results.append({"coalition":list(r.coalition),"separate_seats":r.separate_seats,"coalition_seats":r.coalition_seats,
                        "delta":r.delta,"separate_by_constituency":r.separate_by_constituency,
                        "coalition_by_constituency":r.coalition_by_constituency,"delta_by_constituency":r.delta_by_constituency})
    payload={"status":"DESCRIPTIVE_ONLY","election":"2023","source":matrix["source"],"constituencies":52,"seats":350,
             "party_universe":list(sorted(set(parties))),"coalition_count":len(results),
             "input_hash":sha256_json({"votes":votes,"seats":seats,"valid_votes":valid,"blank_votes":blank,"parties":sorted(set(parties))}),
             "scenarios":results,
             "policy":{"recommendations":False,"ranking_as_best_option":False,"party_personalization":False,
                       "vote_transfer_assumptions":False,"descriptive_math_only":True}}
    OUT_JSON.parent.mkdir(parents=True,exist_ok=True); OUT_MD.parent.mkdir(parents=True,exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Análisis descriptivo neutral de coaliciones — Congreso 2023","",
           "Comparación matemática de candidaturas por separado frente a una lista coaligada. Sin recomendaciones ni optimización política.","",
           f"- Fuente: {matrix['source']}","- Circunscripciones: 52","- Escaños: 350",
           f"- Universo: {len(set(parties))} candidaturas",f"- Escenarios: {len(results)}",f"- Hash de entrada: {payload['input_hash']}","",
           "## Escenarios","",
           "| Coalición | Separado | Coaligado | Delta |","|---|---:|---:|---:|"]
    for x in results: lines.append(f"| {' + '.join(x['coalition'])} | {x['separate_seats']} | {x['coalition_seats']} | {x['delta']} |")
    lines += ["","## Desglose territorial","",
               "El artefacto JSON contiene el desglose completo por circunscripción para cada escenario. Esta sección lista únicamente las circunscripciones cuyo delta no es cero, para mantener el informe legible.",""]
    for x in results:
        changed=[c for c in sorted(x["delta_by_constituency"]) if x["delta_by_constituency"][c] != 0]
        lines.append(f"### {' + '.join(x['coalition'])}")
        if not changed:
            lines.append("Sin variación territorial de escaños.")
        else:
            lines += ["| Circunscripción | Separado | Coaligado | Delta |","|---|---:|---:|---:|"]
            for c in changed:
                lines.append(f"| {c} | {x['separate_by_constituency'][c]} | {x['coalition_by_constituency'][c]} | {x['delta_by_constituency'][c]} |")
        lines.append("")
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"coalition_count":len(results),"json":str(OUT_JSON.relative_to(ROOT)),
                      "report":str(OUT_MD.relative_to(ROOT))},ensure_ascii=False))
if __name__=="__main__": raise SystemExit(main())
