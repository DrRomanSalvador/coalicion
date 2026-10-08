import json
from pathlib import Path
from src.monitoring.healthcheck import healthcheck
from src.backup.backup_restore import create_backup, restore_backup

def test_healthcheck_reads_materialized_state(tmp_path):
    state=tmp_path/"state.json"
    state.write_text(json.dumps({"sources":[{"status":"OK"},{"status":"FAILED"}]}),encoding="utf-8")
    result=healthcheck(state)
    assert result["status"]=="OK"
    assert result["source_count"]==2

def test_backup_roundtrip_is_hash_verified(tmp_path):
    root=tmp_path/"root"; root.mkdir()
    source=root/"critical.json"; source.write_text('{"ok":true}\n',encoding="utf-8")
    backup=tmp_path/"backup.zip"
    manifest=create_backup(root,[source],backup)
    source.unlink()
    result=restore_backup(root,backup,manifest)
    assert result["status"]=="PASS"
    assert source.read_text(encoding="utf-8")=='{"ok":true}\n'
