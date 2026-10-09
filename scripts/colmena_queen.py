#!/usr/bin/env python3
"""COALICIÓN Queen: authoritative planner and swarm coordinator."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs/COLMENA_MISSION_CONTROL.json"
BATCH_SIZE = 5  # verified swarm cycle
WORKER_TIMEOUT_SECONDS = int(os.environ.get("COLMENA_WORKER_TIMEOUT_SECONDS", "600"))
WRITE_WORDS = ("integración física", "conexión", "eliminación", "actualización", "actualizar", "crear", "release", "corregir", "materializar")


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def load():
    if not CONTROL.is_file():
        raise SystemExit("FAIL_CLOSED: mission registry missing")
    d = json.loads(CONTROL.read_text(encoding="utf-8"))
    if d.get("repository") != "DrRomanSalvador/coalicion" or d.get("branch") != "main" or d.get("fail_closed") is not True:
        raise SystemExit("FAIL_CLOSED: invalid mission control contract")
    ms = d.get("missions")
    if not isinstance(ms, list) or len(ms) != 179:
        raise SystemExit(f"FAIL_CLOSED: expected exactly 179 missions, got {len(ms) if isinstance(ms, list) else 0}")
    if any(not isinstance(x, str) or not x.strip() for x in ms):
        raise SystemExit("FAIL_CLOSED: non-atomic/empty mission")
    return d


def mid(i, title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:72]
    return f"M{i:04d}-{slug}"


def classify(title):
    return "WRITE" if any(w in title.lower() for w in WRITE_WORDS) else "READ"


def build_plan(ref):
    d = load()
    missions = []
    for i, title in enumerate(d["missions"], 1):
        missions.append({
            "id": mid(i, title),
            "agent_id": f"agent-{mid(i, title)}",
            "index": i,
            "title": title,
            "kind": classify(title),
            "write_authorized": False,
            "scope": [],
            "depends_on": [],
            "ref": ref,
        })
    ids = [m["id"] for m in missions]
    if len(ids) != len(set(ids)):
        raise SystemExit("FAIL_CLOSED: duplicate mission ids")
    plan = {
        "schema": "COLMENA_EXECUTION_PLAN_V3",
        "repository": "DrRomanSalvador/coalicion",
        "branch": "main",
        "ref": ref,
        "fail_closed": True,
        "batch_size": BATCH_SIZE,
        "missions": missions,
    }
    plan["plan_sha256"] = sha(canon(plan))
    approved = []
    for m in missions:
        token = sha(canon({
            "mission_id": m["id"], "agent_id": m["agent_id"], "ref": m["ref"],
            "plan_sha256": plan["plan_sha256"],
            "write_authorized": m["write_authorized"], "scope": m["scope"],
        }))
        approved.append({**m, "approval": token})
    batches = [
        {"batch": n // BATCH_SIZE + 1, "mission_ids": [m["id"] for m in approved[n:n + BATCH_SIZE]]}
        for n in range(0, len(approved), BATCH_SIZE)
    ]
    return approved, plan, batches


def write_approval(output, ref):
    approved, plan, batches = build_plan(ref)
    out = {
        "schema": "COLMENA_QUEEN_APPROVAL_V3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": plan["plan_sha256"],
        "fail_closed": True,
        "mission_count": len(approved),
        "batch_count": len(batches),
        "batches": batches,
        "missions": approved,
    }
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": "COLMENA_QUEEN_STATE_V2",
        "status": "APPROVED",
        "repository": "DrRomanSalvador/coalicion",
        "branch": "main",
        "ref": ref,
        "plan_sha256": plan["plan_sha256"],
        "mission_count": len(approved),
        "batch_count": len(batches),
        "recoverable": True,
        "agent_runtime_required": True,
        "agent_count": len(approved),
        "coordinator": "scripts/colmena_queen.py",
    }
    out_path.with_name("queen_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "QUEEN_GATE_PASS", "missions": len(approved), "batches": len(batches), "plan_sha256": plan["plan_sha256"]}))


def supervise(approval, ref, workers_dir, state_path):
    d = json.loads(Path(approval).read_text(encoding="utf-8"))
    missions = d.get("missions", [])
    if len(missions) != 179 or d.get("fail_closed") is not True:
        raise SystemExit("FAIL_CLOSED: invalid Queen approval")
    workers = Path(workers_dir)
    workers.mkdir(parents=True, exist_ok=True)
    state_file = Path(state_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    pool_size = int(os.environ.get("COLMENA_AI_SERVER_POOL_SIZE", str(BATCH_SIZE)))
    if pool_size < 1:
        raise SystemExit("FAIL_CLOSED: invalid AI server pool size")

    state = {
        "schema": "COLMENA_QUEEN_STATE_V4",
        "status": "RUNNING",
        "repository": "DrRomanSalvador/coalicion",
        "branch": "main",
        "ref": ref,
        "plan_sha256": d.get("plan_sha256"),
        "mission_count": 179,
        "completed": 0,
        "failed": 0,
        "blocked": 0,
        "batches_total": (179 + BATCH_SIZE - 1) // BATCH_SIZE,
        "batches_completed": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "recoverable": True,
        "parallel_workers": pool_size,
        "execution_mode": "SLIDING_WINDOW_ACROSS_ALL_LOGICAL_BATCHES",
    }

    def persist():
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def dispatch_one(m):
        out = workers / f"worker_{m['index']:04d}.json"
        evidence = None
        if out.exists():
            try:
                existing = json.loads(out.read_text(encoding="utf-8"))
                if (
                    existing.get("mission_id") == m["id"]
                    and existing.get("ref") == ref
                    and existing.get("queen_approval") == m["approval"]
                    and existing.get("agent_id") == m["agent_id"]
                ):
                    evidence = existing
            except Exception:
                evidence = None
        if evidence is not None:
            return evidence

        env = os.environ.copy()
        server_index = (int(m["index"]) - 1) % pool_size
        env["COLMENA_AI_SERVER_URL"] = f"http://127.0.0.1:{int(env.get('COLMENA_AI_SERVER_PORT_BASE', '8765')) + server_index}"
        base_execution_id = env.get("COLMENA_AGENT_EXECUTION_ID", "")
        env["COLMENA_AGENT_EXECUTION_ID"] = f"{base_execution_id}-{m['id']}" if base_execution_id else m["id"]
        print(f"QUEEN_DISPATCH_START={m['id']}", flush=True)
        try:
            p = subprocess.run(
                [sys.executable, "scripts/colmena_worker.py", "--mission-id", m["id"], "--approval", approval, "--ref", ref, "--out", str(out)],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=WORKER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            evidence = {
                "schema": "COLMENA_WORKER_EVIDENCE_V4", "mission_id": m["id"],
                "title": m["title"], "agent_id": m["agent_id"], "status": "BLOCKED",
                "adapter": "WORKER_TIMEOUT", "command": None, "ref": ref,
                "queen_approval": m["approval"], "returncode": 124,
                "stdout": str(exc.stdout or "")[-4000:],
                "stderr": f"FAIL_CLOSED: worker exceeded {WORKER_TIMEOUT_SECONDS}s timeout",
                "agent_runtime": {
                    "provider": env.get("COLMENA_AGENT_PROVIDER", ""),
                    "execution_id": env.get("COLMENA_AGENT_EXECUTION_ID", ""),
                    "independent": True, "ai_execution": True,
                },
            }
            out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"QUEEN_WORKER_TIMEOUT={m['id']}", flush=True)
            return evidence
        try:
            evidence = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            evidence = {"status":"BLOCKED","mission_id":m["id"],"returncode":p.returncode,"stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}
        if p.returncode != 0:
            evidence["_worker_process_returncode"] = p.returncode
        return evidence

    persist()
    batch_pending = {
        batch_no: set(m["id"] for m in missions[start:start + BATCH_SIZE])
        for batch_no, start in enumerate(range(0, len(missions), BATCH_SIZE), 1)
    }
    batch_done = {k: 0 for k in batch_pending}
    active = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as executor:
        future_to_mission = {}
        for m in missions:
            future_to_mission[executor.submit(dispatch_one, m)] = m
            active.add(m["id"])
        for future in concurrent.futures.as_completed(future_to_mission):
            m = future_to_mission[future]
            active.discard(m["id"])
            try:
                evidence = future.result()
            except Exception as exc:
                evidence = {
                    "status": "BLOCKED", "mission_id": m["id"], "title": m["title"],
                    "agent_id": m["agent_id"], "ref": ref, "queen_approval": m["approval"],
                    "returncode": 2, "stderr": f"FAIL_CLOSED: worker exception: {exc}",
                    "agent_runtime": {
                        "provider": os.environ.get("COLMENA_AGENT_PROVIDER", ""),
                        "execution_id": f"{os.environ.get('COLMENA_AGENT_EXECUTION_ID', '')}-{m['id']}",
                        "independent": True, "ai_execution": True,
                    },
                }
                (workers / f"worker_{m['index']:04d}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            status = evidence.get("status")
            state["completed"] += int(status == "PASS")
            state["failed"] += int(status == "FAIL")
            state["blocked"] += int(status not in {"PASS", "FAIL"})
            batch_no = (m["index"] - 1) // BATCH_SIZE + 1
            batch_done[batch_no] += 1
            if batch_done[batch_no] == len(batch_pending[batch_no]):
                state["batches_completed"] += 1
                print(f"QUEEN_BATCH_COMPLETE={batch_no}", flush=True)
            state["current_batch"] = batch_no
            state["current_missions"] = sorted(active)
            persist()

    state["current_batch"] = None
    state["current_missions"] = []
    state["status"] = "PASS" if state["completed"] == 179 and state["failed"] == 0 and state["blocked"] == 0 and state["batches_completed"] == 36 else "BLOCKED"
    persist()
    return 0 if state["status"] == "PASS" else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--supervise", action="store_true")
    ap.add_argument("--workers-dir", default="artifacts/colmena/workers")
    ap.add_argument("--state", default="artifacts/colmena/queen_state.json")
    a = ap.parse_args()
    if a.supervise:
        raise SystemExit(supervise(a.output, a.ref, a.workers_dir, a.state))
    write_approval(a.output, a.ref)


if __name__ == "__main__":
    main()
