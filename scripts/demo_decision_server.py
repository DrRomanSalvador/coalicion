#!/usr/bin/env python3
"""Local decision-demo server; all electoral allocations use the canonical Python engine."""
from __future__ import annotations
import argparse, json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from scripts.demo_multiparty import DEFAULT_DATA, DemoError, load_dataset, git_blob_sha
from scripts.demo_decision_analysis import DEFAULT_JSON, DEFAULT_REPORT, build_analysis, allocate_checked, quotient_boundary

ROOT = Path(__file__).resolve().parents[1]

def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def write_outputs() -> None:
    analysis, report = build_analysis()
    for path, content in ((DEFAULT_JSON, json_bytes(analysis)), (DEFAULT_REPORT, report.encode("utf-8"))):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(content)
        temp.replace(path)

def candidates_for(region: str) -> dict:
    dataset, regions, raw = load_dataset(DEFAULT_DATA)
    if region not in ("Madrid", "Barcelona"):
        raise ValueError("Circunscripción no admitida.")
    item = regions[region]
    return {
        "schema": "COALICION_CUSTOM_CANDIDATES_V1",
        "region": region,
        "magnitude": item["seats"],
        "valid_votes": item["valid_votes"],
        "blank_votes": item["blank_votes"],
        "candidates": [
            {"name": p, "votes": v, "observed_seats": item["observed_seats"].get(p, 0)}
            for p, v in sorted(item["parties"].items(), key=lambda pair: (-pair[1], pair[0]))
        ],
        "source": dataset["source"],
        "canonical_dataset_git_blob_sha1": git_blob_sha(raw),
    }

def simulate_custom_coalition(payload: dict) -> dict:
    if not isinstance(payload, dict): raise ValueError("El cuerpo debe ser un objeto JSON.")
    region, members, label = payload.get("region"), payload.get("members"), payload.get("label", "Coalición personalizada")
    if region not in ("Madrid", "Barcelona"): raise ValueError("Circunscripción no admitida.")
    if not isinstance(label, str) or not label.strip() or len(label.strip()) > 100: raise ValueError("Nombre de coalición inválido.")
    if not isinstance(members, list) or len(members) < 2 or any(not isinstance(p, str) for p in members):
        raise ValueError("Selecciona al menos dos candidaturas.")
    if len(set(members)) != len(members): raise ValueError("Hay candidaturas duplicadas.")
    dataset, regions, raw = load_dataset(DEFAULT_DATA)
    item = regions[region]
    votes = item["parties"]
    unknown = sorted(set(members) - set(votes))
    if unknown: raise ValueError("Candidaturas no encontradas: " + ", ".join(unknown))
    if label.strip() in set(votes) - set(members): raise ValueError("El nombre de la coalición coincide con una candidatura que quedaría separada.")
    base = allocate_checked(votes, item["seats"], item["blank_votes"])
    grouped_votes = sum(votes[p] for p in members)
    lists = {p: v for p, v in votes.items() if p not in members}
    lists[label.strip()] = grouped_votes
    if sum(lists.values()) != sum(votes.values()): raise ValueError("La agrupación no conserva los votos.")
    joined = allocate_checked(lists, item["seats"], item["blank_votes"])
    before = sum(base.get(p, 0) for p in members)
    after = joined.get(label.strip(), 0)
    return {
        "schema": "COALICION_CUSTOM_SIMULATION_V1",
        "status": "OK",
        "region": region,
        "coalition_label": label.strip(),
        "members": [{"name": p, "votes": votes[p], "observed_seats": base.get(p, 0)} for p in members],
        "coalition_votes": grouped_votes,
        "seats_separate_total": before,
        "seats_coalition": after,
        "seat_delta": after - before,
        "member_seats_in_separate_lists_absorbed": {p: base.get(p, 0) for p in members},
        "simulated_seats": {p: n for p, n in joined.items() if n},
        "valid_votes_before": item["valid_votes"],
        "valid_votes_after": item["valid_votes"],
        "votes_conserved": sum(lists.values()) == sum(votes.values()),
        "blank_votes_fixed": item["blank_votes"],
        "marginal_quotient_explanation": quotient_boundary(lists, joined, label.strip()) if after > before else {"status": "NO_GAIN_IN_COALITION_SEATS"},
        "method": "src.electoral.allocate; D’Hondt y umbral legal canónico",
        "assumption": "Suma mecánica de los votos observados de 2023; cero transferencias modeladas.",
        "not_a_prediction": True,
        "official_certification": "NOT_INDEPENDENTLY_CERTIFIED",
        "source_url": dataset["source"]["url"],
    }

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def send_json(self, status: int, value: dict):
        raw = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json(200, {"status": "OK", "service": "COALICION_DECISION_DEMO_V1"})
        if parsed.path == "/api/candidates":
            try:
                region = parse_qs(parsed.query).get("region", [""])[0]
                return self.send_json(200, candidates_for(region))
            except (ValueError, DemoError, OSError) as exc:
                return self.send_json(400, {"status": "BLOCKED", "error": str(exc)})
        if parsed.path == "/api/analysis":
            try:
                return self.send_json(200, json.loads(DEFAULT_JSON.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                return self.send_json(503, {"status": "BLOCKED", "error": "Registro no generado; reinicia el servidor para materializarlo.", "detail": str(exc)})
        return super().do_GET()
    def do_POST(self):
        if urlparse(self.path).path != "/api/simulate":
            return self.send_json(404, {"status": "BLOCKED", "error": "Endpoint desconocido."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 65536: raise ValueError("Tamaño de solicitud inválido.")
            payload = json.loads(self.rfile.read(length))
            return self.send_json(200, simulate_custom_coalition(payload))
        except (ValueError, json.JSONDecodeError, DemoError, OSError, RuntimeError, KeyError, TypeError) as exc:
            return self.send_json(400, {"status": "BLOCKED", "error": str(exc)})
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error("--port debe estar entre 1 y 65535.")
    write_outputs()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"COALICIÓN demo disponible en http://{args.host}:{args.port}/web/demo/")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
