#!/usr/bin/env python3
"""Queen Gate: validates and compiles the executable atomic mission plan."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs/COLMENA_MISSION_CONTROL.json"
BATCH_SIZE = 5
WRITE_WORDS = ("integración física", "conexión", "eliminación", "actualización", "crear", "release", "corregir", "materializar")

def canon(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def load():
    if not CONTROL.is_file():
        raise SystemExit("FAIL_CLOSED: mission registry missing")
    d = json.loads(CONTROL.read_text(encoding="utf-8"))
    if d.get("repository") != "DrRomanSalvador/coalicion" or d.get("branch") != "main" or d.get("fail_closed") is not True:
        raise SystemExit("FAIL_CLOSED: invalid mission control contract")
    ms = d.get("missions")
    if not isinstance(ms, list) or not ms:
        raise SystemExit("FAIL_CLOSED: empty mission registry")
    if any(not isinstance(x, str) or not x.strip() for x in ms):
        raise SystemExit("FAIL_CLOSED: non-atomic/empty mission")
    if len(ms) != 179:
        raise SystemExit(f"FAIL_CLOSED: expected exactly 179 missions, got {len(ms)}")
    # Repeated text is allowed: each list position is a distinct user mission.
    # IDs are ordinal-bound, so repeated titles cannot collapse workers.
    return d

def mid(i, title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:72]
    return f"M{i:04d}-{slug}"

def classify(title):
    low = title.lower()
    return "WRITE" if any(w in low for w in WRITE_WORDS) else "READ"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    d = load()
    missions = []
    for i, title in enumerate(d["missions"], 1):
        missions.append({
            "id": mid(i, title),
            "index": i,
            "title": title,
            "kind": classify(title),
            "write_authorized": False,
            "scope": [],
            "depends_on": [],
            "ref": a.ref,
        })
    plan = {
        "schema": "COLMENA_EXECUTION_PLAN_V2",
        "repository": "DrRomanSalvador/coalicion",
        "branch": "main",
        "ref": a.ref,
        "fail_closed": True,
        "batch_size": BATCH_SIZE,
        "missions": missions,
    }
    ids = [m["id"] for m in missions]
    if len(ids) != len(set(ids)):
        raise SystemExit("FAIL_CLOSED: duplicate mission ids")
    for m in missions:
        if m["write_authorized"] and not m["scope"]:
            raise SystemExit("FAIL_CLOSED: write mission without scope: " + m["id"])
    plan["plan_sha256"] = sha(canon(plan))
    approved = []
    for m in missions:
        token = sha(canon({
            "mission_id": m["id"], "ref": m["ref"],
            "plan_sha256": plan["plan_sha256"],
            "write_authorized": m["write_authorized"], "scope": m["scope"],
        }))
        approved.append({**m, "approval": token})
    batches = []
    for n in range(0, len(approved), BATCH_SIZE):
        chunk = approved[n:n+BATCH_SIZE]
        batches.append({"batch": n // BATCH_SIZE + 1, "mission_ids": [m["id"] for m in chunk]})
    out = {
        "schema": "COLMENA_QUEEN_APPROVAL_V2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": plan["plan_sha256"],
        "fail_closed": True,
        "mission_count": len(approved),
        "batch_count": len(batches),
        "batches": batches,
        "missions": approved,
    }
    out_path = Path(a.output)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = {"schema":"COLMENA_QUEEN_STATE_V1","status":"APPROVED","repository":"DrRomanSalvador/coalicion","branch":"main","ref":a.ref,"plan_sha256":plan["plan_sha256"],"mission_count":len(approved),"batch_count":len(batches),"recoverable":True}
    out_path.with_name("queen_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "QUEEN_GATE_PASS", "missions": len(approved), "batches": len(batches), "plan_sha256": plan["plan_sha256"]}))

if __name__ == "__main__":
    main()
