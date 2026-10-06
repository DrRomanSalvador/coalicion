#!/usr/bin/env python3
"""
Materialización reproducible de fuentes oficiales para REINA-SEEC.

Política:
- Fuentes históricas/estables: se descargan y se conservan localmente con SHA-256.
- Fuentes vivas: se indexan contra su URL primaria y, cuando se adquieren, se
  conserva un snapshot con SHA-256.
- Nunca se sustituye una fuente primaria por una secundaria.
- Los fallos de descarga se registran y provocan código de salida != 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "official"
MANIFESTS = ROOT / "data" / "manifests"
LIVE = ROOT / "data" / "live"
PROCESSED = ROOT / "data" / "processed"
LOG = ROOT / "artifacts" / "execution_log.md"

SOURCES = {
    "interior": {
        "source_id": "INTERIOR_RESULTADOS_CONGRESO",
        "authority": "Ministerio del Interior",
        "url": "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx",
        "catalog_url": "https://datos.gob.es/es/catalogo/e00003801-resultados-electorales",
        "path": RAW / "Elecciones-Congreso.xlsx",
        "manifest": MANIFESTS / "INTERIOR_RESULTADOS_CONGRESO.json",
    },
    "ine": {
        "source_id": "INE_PADRON_MUNICIPAL",
        "authority": "Instituto Nacional de Estadística",
        "url": "https://www.ine.es/pob_xls/pobmun.zip",
        "catalog_url": "https://www.ine.es/dynt3/inebase/es/index.htm?padre=525",
        "path": RAW / "ine" / "pobmun.zip",
        "manifest": MANIFESTS / "INE_PADRON_MUNICIPAL.json",
    },
    "cis": {
        "source_id": "CIS_CATALOGO_ESTUDIOS",
        "authority": "Centro de Investigaciones Sociológicas",
        "url": "https://www.cis.es/es/estudios/catalogo?catalogo=estudio",
        "path": LIVE / "CIS_CATALOGO_ESTUDIOS.html",
        "manifest": LIVE / "CIS_CATALOGO_ESTUDIOS.json",
    },
    "boe": {
        "source_id": "BOE_LEGISLACION",
        "authority": "Boletín Oficial del Estado",
        "url": "https://www.boe.es/",
        "path": LIVE / "BOE_LEGISLACION.html",
        "manifest": LIVE / "BOE_LEGISLACION.json",
    },
    "jec": {
        "source_id": "JEC",
        "authority": "Junta Electoral Central",
        "url": "https://www.juntaelectoralcentral.es/",
        "path": LIVE / "JEC.html",
        "manifest": LIVE / "JEC.json",
    },
}

USER_AGENT = "REINA-SEEC/1.0 (+https://github.com/DrRomanSalvador/coalicion)"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"- {now()} — {message}\n")


def download(url: str, destination: Path, timeout: int = 120) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("descarga vacía")
        tmp.replace(destination)
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError):
        tmp.unlink(missing_ok=True)
        raise
    return {
        "retrieved_at": now(),
        "path": str(destination.relative_to(ROOT)),
        "size_bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }


def write_manifest(cfg: dict, acquired: dict) -> None:
    cfg["manifest"].parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_id": cfg["source_id"],
        "authority": cfg["authority"],
        "source_url": cfg["url"],
        "catalog_url": cfg.get("catalog_url"),
        **acquired,
    }
    cfg["manifest"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def materialize_binary(name: str, force: bool) -> bool:
    cfg = SOURCES[name]
    if cfg["path"].exists() and not force:
        acquired = {
            "retrieved_at": now(),
            "path": str(cfg["path"].relative_to(ROOT)),
            "size_bytes": cfg["path"].stat().st_size,
            "sha256": sha256(cfg["path"]),
            "status": "already_present",
        }
        write_manifest(cfg, acquired)
        log(f"{cfg['source_id']}: ya materializado; SHA-256={acquired['sha256']}")
        return True

    try:
        acquired = download(cfg["url"], cfg["path"])
        acquired["status"] = "downloaded"
        write_manifest(cfg, acquired)
        log(f"{cfg['source_id']}: descargado; SHA-256={acquired['sha256']}")
        return True
    except Exception as exc:
        log(f"{cfg['source_id']}: ERROR de descarga: {type(exc).__name__}: {exc}")
        return False


def materialize_live(name: str, force: bool) -> bool:
    cfg = SOURCES[name]
    try:
        if cfg["path"].exists() and not force:
            acquired = {
                "retrieved_at": now(),
                "path": str(cfg["path"].relative_to(ROOT)),
                "size_bytes": cfg["path"].stat().st_size,
                "sha256": sha256(cfg["path"]),
                "status": "snapshot_already_present",
            }
        else:
            acquired = download(cfg["url"], cfg["path"])
            acquired["status"] = "snapshot_acquired"

        payload = {
            "source_id": cfg["source_id"],
            "authority": cfg["authority"],
            "source_url": cfg["url"],
            "retrieved_at": acquired["retrieved_at"],
            "snapshot_path": acquired["path"],
            "size_bytes": acquired["size_bytes"],
            "sha256": acquired["sha256"],
            "mode": "LIVE_INDEX_WITH_SNAPSHOT",
        }
        cfg["manifest"].parent.mkdir(parents=True, exist_ok=True)
        cfg["manifest"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        log(f"{cfg['source_id']}: índice vivo + snapshot; SHA-256={acquired['sha256']}")
        return True
    except Exception as exc:
        log(f"{cfg['source_id']}: ERROR de fuente viva: {type(exc).__name__}: {exc}")
        return False


def normalize_interior() -> bool:
    source = SOURCES["interior"]["path"]
    output = PROCESSED / "congress_rows.json"
    try:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        cli = ROOT / "cli.py"
        if not cli.exists():
            raise FileNotFoundError("cli.py no existe")
        subprocess.run(
            [sys.executable, str(cli), "inspect", str(source)],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [
                sys.executable, str(cli), "normalize", str(source),
                "--output", str(output),
            ],
            cwd=ROOT,
            check=True,
        )
        log(f"INTERIOR: normalización correcta en {output.relative_to(ROOT)}")
        return True
    except Exception as exc:
        log(f"INTERIOR: ERROR de normalización: {type(exc).__name__}: {exc}")
        return False


def materialize(selected: list[str], force: bool, normalize: bool) -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log("INICIO materializar_fuentes_oficiales.py")
    failures = []

    for name in selected:
        ok = (
            materialize_binary(name, force)
            if name in {"interior", "ine"}
            else materialize_live(name, force)
        )
        if not ok:
            failures.append(name)

    if normalize and "interior" in selected and "interior" not in failures:
        if not normalize_interior():
            failures.append("normalize:interior")

    if failures:
        log("FIN CON ERRORES: " + ", ".join(failures))
        return 1

    log("FIN OK")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Descarga, materializa, hashea e indexa fuentes oficiales."
    )
    p.add_argument(
        "--all", action="store_true",
        help="Materializa todas las fuentes configuradas."
    )
    p.add_argument(
        "--source", choices=sorted(SOURCES), action="append",
        help="Fuente a materializar; puede repetirse."
    )
    p.add_argument(
        "--force", action="store_true",
        help="Vuelve a descargar aunque exista un snapshot local."
    )
    p.add_argument(
        "--no-normalize", action="store_true",
        help="No ejecutar la normalización de Interior."
    )
    p.add_argument(
        "--year", default=None,
        help="Compatibilidad de interfaz; el dataset oficial de Interior contiene el histórico."
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.all:
        selected = list(SOURCES)
    elif args.source:
        selected = list(dict.fromkeys(args.source))
    else:
        selected = ["interior", "ine", "cis", "boe", "jec"]

    if args.year not in (None, "2023"):
        print("ERROR: solo se admite --year 2023 con la interfaz actual.", file=sys.stderr)
        return 2

    return materialize(
        selected,
        force=args.force,
        normalize=not args.no_normalize,
    )


if __name__ == "__main__":
    raise SystemExit(main())
