"""CLI mínima de COALICIÓN Decision Engine."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from src.decision import coalition_result, apply_absolute_shift, Scenario, validate_scenario, sha256_json
from src.coalition_decision import coalition_decision
from src.prediction_engine import predict
from src.electoral import allocate

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def cmd_audit(a):
    anchor=Path("data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json")
    if a.election!="2023": raise SystemExit("Solo 2023 está conectado en el MVP")
    if not anchor.exists(): raise SystemExit("BLOCKED: falta ancla primaria")
    d=json.loads(anchor.read_text(encoding="utf-8"))
    print(json.dumps({"election":"2023","source_status":"PRIMARY_ANCHOR_PRESENT","source_sha256":d.get("sha256"),"certification_status":"BLOCKED","reason":"primary binary must be materialized and semantically reconciled"},ensure_ascii=False,indent=2))
def cmd_verify(a):
    p=Path(a.certificate)
    if not p.exists(): raise SystemExit("BLOCKED: certificado inexistente")
    d=json.loads(p.read_text(encoding="utf-8"))
    print(json.dumps({"certificate":str(p),"status":d.get("status"),"verified":d.get("status")=="CERTIFIED"},ensure_ascii=False,indent=2))
def cmd_coalition(a):
    d=load(a.input); r=coalition_result(d["votes"],d["seats"],d["valid_votes"],tuple(a.parties),d.get("special"),d.get("blank")); print(json.dumps(r,ensure_ascii=False,indent=2))
def cmd_coalition_report(a):
    d=load(a.input)
    r=coalition_decision(d["votes"],d["seats"],d.get("blank",{c:0 for c in d["votes"]}),tuple(a.parties),d.get("special"))
    print(json.dumps(r,ensure_ascii=False,indent=2))

def cmd_predict(a):
    d=load(a.input)
    changes=d["share_changes"]
    factors=d.get("turnout_factors",{})
    r=predict(d["votes"],d["seats"],d.get("blank",{c:0 for c in d["votes"]}),changes,factors,d.get("special"))
    print(json.dumps(r,ensure_ascii=False,indent=2))

def cmd_scenario(a):
    d=load(a.input); dist=a.distribution or "unspecified"
    s=Scenario("national_shift",a.party,"absolute_points",a.shift,dist,("no turnout change","no vote transfer"),"user_defined","none"); validate_scenario(s)
    votes=apply_absolute_shift(d["votes"],a.party,a.shift,dist); result={}
    for c,row in votes.items():
        x=allocate(row,d["seats"][c],sum(row.values()),d.get("special",{}).get(c,""),d.get("blank",{}).get(c,0))
        if x.status!="OK": raise SystemExit(f"BLOCKED: {c}: {x.status}")
        result[c]=x.seats
    print(json.dumps({"scenario":s.__dict__,"votes":votes,"seats":result,"input_hash":sha256_json(d["votes"]),"output_hash":sha256_json(result)},ensure_ascii=False,indent=2))
def main():
    p=argparse.ArgumentParser(prog="coalicion",description="Auditoría y simulación electoral reproducible"); sub=p.add_subparsers(dest="cmd",required=True)
    au=sub.add_parser("audit"); au.add_argument("election"); au.set_defaults(fn=cmd_audit)
    ve=sub.add_parser("verify"); ve.add_argument("certificate"); ve.set_defaults(fn=cmd_verify)
    c=sub.add_parser("coalition"); c.add_argument("parties",nargs="+"); c.add_argument("--input",required=True); c.set_defaults(fn=cmd_coalition)
    cr=sub.add_parser("coalition-report"); cr.add_argument("parties",nargs="+"); cr.add_argument("--input",required=True); cr.set_defaults(fn=cmd_coalition_report)
    pr=sub.add_parser("predict"); pr.add_argument("--input",required=True); pr.set_defaults(fn=cmd_predict)
    s=sub.add_parser("scenario"); s.add_argument("--party",required=True); s.add_argument("--shift",type=float,required=True); s.add_argument("--distribution",choices=["uniform_by_province","unspecified"],default="unspecified"); s.add_argument("--input",required=True); s.set_defaults(fn=cmd_scenario)
    sub.add_parser("version").set_defaults(fn=lambda a: print("COALICIÓN Decision Engine 0.1")); a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
