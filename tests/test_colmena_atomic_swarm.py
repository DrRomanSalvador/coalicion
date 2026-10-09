from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/"docs/COLMENA_MISSION_CONTROL.json"

def test_queen_plan_covers_every_mission(tmp_path):
    out=tmp_path/"approval.json"
    p=subprocess.run([sys.executable,"scripts/colmena_queen.py","--ref","test-ref","--output",str(out)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0, p.stderr
    d=json.loads(out.read_text())
    registry=json.loads(CONTROL.read_text())
    assert len(d["missions"])==len(registry["missions"])
    assert len({m["id"] for m in d["missions"]})==len(d["missions"])
    assert all(m["write_authorized"] is False for m in d["missions"])

def test_worker_rejects_tampered_approval(tmp_path):
    out=tmp_path/"approval.json"
    subprocess.run([sys.executable,"scripts/colmena_queen.py","--ref","test-ref","--output",str(out)],cwd=ROOT,check=True)
    d=json.loads(out.read_text())
    d["missions"][0]["approval"]="tampered"
    out.write_text(json.dumps(d),encoding="utf-8")
    ev=tmp_path/"evidence.json"
    p=subprocess.run([sys.executable,"scripts/colmena_worker.py","--mission-id",d["missions"][0]["id"],"--approval",str(out),"--ref","test-ref","--out",str(ev)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode!=0

def test_workflow_binds_reina_secret_without_printing_it():
    workflow=(ROOT/".github/workflows/colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert "HF_TOKEN: ${{ secrets.reina_TOKEN }}" in workflow
    assert "if [[ -z \"${HF_TOKEN:-}\" ]]" in workflow
    assert "echo \"${HF_TOKEN}" not in workflow
    assert "print(\"${HF_TOKEN}" not in workflow
    assert "Persist operational state (fail-closed)" in workflow
    assert "timestamp_europe_madrid" in workflow
