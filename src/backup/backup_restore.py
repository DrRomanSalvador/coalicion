"""Deterministic ZIP backup with path-traversal-safe restore."""
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path

def _sha(path: Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def create_backup(root: Path, files: list[Path], output: Path)->dict:
    records=[]
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(files,key=lambda p:str(p)):
            resolved=path.resolve()
            resolved.relative_to(root.resolve())
            if not resolved.is_file(): raise FileNotFoundError(resolved)
            arc=str(resolved.relative_to(root.resolve()))
            z.write(resolved,arc)
            records.append({"path":arc,"sha256":_sha(resolved)})
    manifest={"schema":"COALICION_BACKUP_V1","files":records,"fail_closed":True}
    return manifest

def restore_backup(root: Path, backup: Path, manifest: dict)->dict:
    root=root.resolve()
    restored=[]
    with zipfile.ZipFile(backup) as z:
        names=set(z.namelist())
        expected={str(x["path"]):str(x["sha256"]) for x in manifest.get("files",[])}
        if names != set(expected): raise ValueError("BLOCKED_BACKUP_MANIFEST_MISMATCH")
        for name, digest in expected.items():
            target=(root/name).resolve()
            target.relative_to(root)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(name))
            if _sha(target)!=digest: raise ValueError("BLOCKED_BACKUP_HASH_MISMATCH")
            restored.append(name)
    return {"status":"PASS","restored":sorted(restored),"fail_closed":True}
