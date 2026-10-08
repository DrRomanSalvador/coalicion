#!/usr/bin/env python3
"""Minimal production API for COALICIÓN.

No framework dependency: standard-library HTTP server, API-key auth, bounded
rate limiting and JSON audit. Predictive endpoints fail closed unless the
corresponding materialized evidence is genuinely promotable.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("COALICION_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("COALICION_API_PORT", "8080"))
API_KEY = os.environ.get("COALICION_API_KEY", "").strip()
RATE_LIMIT = int(os.environ.get("COALICION_API_RATE_LIMIT", "60"))
RATE_WINDOW = 60.0
AUDIT = ROOT / "artifacts" / "api_audit.jsonl"
_lock = threading.Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _audit(client: str, path: str, status: int) -> None:
    record = {
        "ts": time.time(),
        "client_hash": hashlib.sha256(client.encode()).hexdigest(),
        "path": path,
        "status": status,
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _rate_allowed(client: str) -> bool:
    now = time.monotonic()
    with _lock:
        q = _buckets[client]
        while q and now - q[0] >= RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "COALICION-API/1"

    def log_message(self, *_args):
        return

    def _send(self, status: int, payload: dict) -> None:
        body = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _auth(self) -> bool:
        if not API_KEY:
            self._send(503, {"status": "BLOCKED", "reason": "COALICION_API_KEY is not configured"})
            return False
        supplied = self.headers.get("X-API-Key", "")
        if not supplied or not hashlib.sha256(supplied.encode()).digest() == hashlib.sha256(API_KEY.encode()).digest():
            self._send(401, {"status": "UNAUTHORIZED"})
            return False
        client = self.client_address[0]
        if not _rate_allowed(client):
            self._send(429, {"status": "RATE_LIMITED"})
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        client = self.client_address[0]
        if path == "/healthz":
            self._send(200, {"status": "OK", "service": "coalicion-api"})
            return
        if not self._auth():
            try:
                _audit(client, path, 401)
            except OSError:
                pass
            return

        if path == "/estado":
            from scripts.product_status import product_status
            payload = product_status(str(ROOT))
            self._send(200, payload)
        elif path == "/encuestas":
            payload = _json(ROOT / "artifacts/estimation/observations.json")
            if not payload.get("polls"):
                current = _json(ROOT / "data/surveys/current_2026/current_national.json")
                payload = {
                    "schema": current.get("schema", "CURRENT_NATIONAL_SURVEY_REGISTRY_V1"),
                    "as_of": current.get("as_of"),
                    "surveys": current.get("surveys", []),
                    "evidence_policy": current.get("policy", {}),
                }
            self._send(200, {"status": "OK", **payload})
        elif path == "/prediccion-demo":
            payload = _json(ROOT / "artifacts/territorial_prediction_20261008.json")
            if not payload:
                self._send(404, {"status": "NOT_FOUND", "reason": "Demo prediction is not materialized"})
            else:
                self._send(200, payload)
        elif path == "/demo":
            current = _json(ROOT / "data/surveys/current_2026/current_national.json")
            prediction = _json(ROOT / "artifacts/territorial_prediction_20261008.json")
            self._send(200, {
                "status": "DEMO_NON_OFFICIAL",
                "surveys": current,
                "territorial_prediction": prediction,
                "external_audit_required": True,
            })
        elif path == "/evidencia":
            payload = {
                "seec": _json(ROOT / "ci_evidence/seec_production.json"),
                "mc_10000": _json(ROOT / "ci_evidence/mc_10000.json"),
                "oos": _json(ROOT / "ci_evidence/oos_calibration.json"),
                "master": _json(ROOT / "ci_evidence/master_certification.json"),
            }
            self._send(200, {"status": "OK", "evidence": payload})
        elif path == "/territorio":
            matrix = _json(ROOT / "artifacts/data/election_2023_canonical.json")
            self._send(200, {"status": "OK", "election": "2023", "matrix": matrix})
        elif path == "/prediccion":
            estimation = _json(ROOT / "artifacts/estimation/real_estimation.json")
            if str(estimation.get("status", "")).upper() not in {"PASS", "CERTIFIED"}:
                self._send(409, {
                    "status": "NOT_CERTIFIED",
                    "reason": "No existe una predicción territorial 2026 certificada.",
                })
            else:
                self._send(200, estimation)
        else:
            self._send(404, {"status": "NOT_FOUND"})
        try:
            _audit(client, path, 200)
        except OSError:
            pass


def main() -> int:
    if not API_KEY:
        raise SystemExit("BLOCKED: configure COALICION_API_KEY before starting production API")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"COALICION API listening on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
