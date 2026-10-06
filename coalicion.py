"""CLI mínima de COALICIÓN Decision Engine."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.decision_engine import coalition_result, apply_absolute_shift, Scenario, validate_scenario, sha256_json
from src.electoral import allocate

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def cmd_coalition(a):
    d=load(a.input); r=coalition_result(d["votes"],d["seats"],d["valid_votes"],tuple(a.parties),d.get("special"),d.get("blank")); print(json.dumps(r,ensure_ascii=False,indent=2))
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
    c=sub.add_parser("coalition"); c.add_argument("parties",nargs="+"); c.add_argument("--input",required=True); c.set_defaults(fn=cmd_coalition)
    s=sub.add_parser("scenario"); s.add_argument("--party",required=True); s.add_argument("--shift",type=float,required=True); s.add_argument("--distribution",choices=["uniform_by_province","unspecified"],default="unspecified"); s.add_argument("--input",required=True); s.set_defaults(fn=cmd_scenario)
    sub.add_parser("version").set_defaults(fn=lambda a: print("COALICIÓN Decision Engine 0.1")); a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
