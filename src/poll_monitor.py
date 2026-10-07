#!/usr/bin/env python3
"""Autonomous, fail-closed polling monitor with longitudinal provenance.

The monitor distinguishes three things deliberately:
1. validated polls with party-level estimates;
2. source discoveries whose page/feed changed but whose values are not machine-verifiable;
3. blocked sources/parsers.

It never derives territorial votes or seats from national percentages.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import date
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "poll_monitor.json"
STATE = ROOT / "artifacts" / "poll_monitor_state.json"
SURVEYS = ROOT / "artifacts" / "surveys"
HISTORY = ROOT / "artifacts" / "survey_history.jsonl"

ALIASES = {
    "PSOE": "PSOE", "PARTIDO SOCIALISTA OBRERO ESPAÑOL": "PSOE",
    "PP": "PP", "PARTIDO POPULAR": "PP",
    "VOX": "VOX", "SUMAR": "SUMAR", "PODEMOS": "PODEMOS",
    "IU": "IU", "IZQUIERDA UNIDA": "IU", "MÁS PAÍS": "MÁS PAÍS",
    "MAS PAIS": "MÁS PAÍS", "ERC": "ERC", "ESQUERRA": "ERC",
    "JUNTS": "JUNTS", "PNV": "PNV", "EAJ-PNV": "PNV",
    "EH BILDU": "EH BILDU", "BILDU": "EH BILDU", "BNG": "BNG",
    "CC": "CC", "CCA": "CC", "UPN": "UPN", "PACMA": "PACMA",
    "SE ACABÓ LA FIESTA": "SE ACABÓ LA FIESTA",
    "SALF": "SE ACABÓ LA FIESTA",
    "OTROS PARTIDOS": "OTROS PARTIDOS",
}

@dataclass(frozen=True)
class Poll:
    poll_id: str
    publication_date: str
    pollster: str
    source_id: str
    source_url: str
    parties: dict[str, float]
    fieldwork_start: str | None = None
    fieldwork_end: str | None = None
    sample_size: int | None = None
    methodology: str | None = None
    validation: str = "VALIDATED"

def normalize_party_name(name: str) -> str:
    key = re.sub(r"\s+", " ", str(name).strip().upper())
    return ALIASES.get(key, str(name).strip().upper())

def poll_hash(poll: Poll) -> str:
    payload = {
        "poll_id": poll.poll_id, "publication_date": poll.publication_date,
        "pollster": poll.pollster, "source_id": poll.source_id,
        "source_url": poll.source_url, "parties": dict(sorted(poll.parties.items())),
        "fieldwork_start": poll.fieldwork_start, "fieldwork_end": poll.fieldwork_end,
        "sample_size": poll.sample_size, "methodology": poll.methodology,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()

def canonical_poll(poll: Poll) -> dict[str, Any]:
    return asdict(poll)

def validate_poll(poll: Poll, *, min_parties: int = 5) -> tuple[bool, str]:
    if len(poll.parties) < min_parties:
        return False, "INSUFFICIENT_PARTY_VALUES"
    values = list(poll.parties.values())
    if any(v != v or v < 0 or v > 100 for v in values):
        return False, "INVALID_PERCENTAGE"
    if not poll.publication_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", poll.publication_date):
        return False, "INVALID_PUBLICATION_DATE"
    try:
        date.fromisoformat(poll.publication_date)
    except ValueError:
        return False, "INVALID_PUBLICATION_DATE"
    if not poll.pollster.strip() or not poll.source_id.strip():
        return False, "MISSING_SOURCE_METADATA"
    total = sum(values)
    # Published tables may omit residual categories, so validation accepts
    # 95-105% but never manufactures the missing mass.
    if not 95 <= total <= 105:
        return False, f"PARTY_TOTAL_OUTSIDE_95_105:{total:.3f}"
    return True, "OK"

def _parse_date(text: str) -> str | None:
    text = text.strip()
    for pattern in (r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
                    r"(\d{1,2}) de ([A-Za-záéíóú]+) de (\d{4})"):
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        if len(m.groups()) == 3 and m.group(2).isdigit():
            return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None

def parse_dato_electoral(html: bytes, source: dict[str, Any]) -> list[Poll]:
    """Parse only Dato Electoral's explicitly labelled published estimates."""
    soup = BeautifulSoup(html, "html.parser")
    months = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
              "julio":7,"agosto":8,"septiembre":9,"octubre":10,
              "noviembre":11,"diciembre":12}
    out: list[Poll] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        label = heading.get_text(" ", strip=True)
        if "Estimación de voto publicada por el sondeo" not in label:
            continue
        section: list[str] = []
        for node in heading.find_all_next():
            if node is not heading and node.name in {"h2","h3","h4"} and section:
                break
            text = node.get_text(" ", strip=True)
            if text:
                section.append(text)
        meta = []
        for node in heading.find_all_previous():
            if node.name in {"h2","h3"}:
                break
            text = node.get_text(" ", strip=True)
            if text:
                meta.append(text)
        parent = " ".join(reversed(meta))
        title = next((h.get_text(" ", strip=True)
                      for h in heading.find_all_previous(["h2","h3"])
                      if h.get_text(" ", strip=True)), "Encuesta")
        m = re.search(r"publicado el (\d{1,2}) de ([a-záéíóú]+) de (\d{4})",
                      parent, re.I)
        if not m or m.group(2).lower() not in months:
            continue
        publication = f"{m.group(3)}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        parties: dict[str, float] = {}
        for line in section:
            pm = re.match(r"^(.+?)\s+([0-9]+(?:[.,][0-9]+)?)\s*%$", line)
            if not pm:
                continue
            party = normalize_party_name(pm.group(1))
            if party in set(ALIASES.values()):
                parties[party] = float(pm.group(2).replace(",", "."))
        if not parties:
            continue
        sample = None
        sm = re.search(r"Tamaño de la muestra\s*:?\s*(\d[\d.]*)", parent, re.I)
        if sm:
            sample = int(sm.group(1).replace(".", ""))
        poll = Poll(
            poll_id=f"{source['id']}::{publication}::{title}",
            publication_date=publication,
            pollster=parent.split(" · publicado el ")[0].strip() or "Fuente publicada",
            source_id=source["id"], source_url=source["url"], parties=parties,
            sample_size=sample,
        )
        ok, reason = validate_poll(poll)
        if ok:
            out.append(poll)
    return out

def parse_rss_metadata(body: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source discoveries; RSS is not treated as party-level evidence."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(body.decode("utf-8"))
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or source["url"]).strip()
        pub = (item.findtext("pubDate") or item.findtext("published") or "").strip()
        guid = (item.findtext("guid") or link or title).strip()
        if title and guid:
            out.append({
                "discovery_id": guid, "title": title, "link": link,
                "publication_raw": pub, "source_id": source["id"],
                "validation": "DISCOVERY_ONLY", "alertable": True,
            })
    return out

def parse_electomania_json(body: bytes, source: dict[str, Any]) -> list[Poll]:
    data = json.loads(body.decode("utf-8"))
    if isinstance(data, dict):
        data = data.get("encuestas", data.get("polls", data.get("data")))
    if not isinstance(data, list):
        raise ValueError("Electomania JSON has no recognised poll array")
    out = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        parties_raw = raw.get("parties") or raw.get("estimacion") or raw.get("estimation")
        if not isinstance(parties_raw, dict):
            continue
        parties = {normalize_party_name(k): float(str(v).replace("%","").replace(",","."))
                   for k,v in parties_raw.items()}
        poll = Poll(
            poll_id=str(raw.get("id") or raw.get("poll_id") or
                        f"{source['id']}::{raw.get('date') or raw.get('publication_date')}::{raw.get('pollster','')}"),
            publication_date=str(raw.get("publication_date") or raw.get("date") or "")[:10],
            pollster=str(raw.get("pollster") or raw.get("source") or "Electomanía").strip(),
            source_id=source["id"], source_url=source["url"], parties=parties,
            fieldwork_start=raw.get("fieldwork_start"), fieldwork_end=raw.get("fieldwork_end"),
            sample_size=raw.get("sample_size"),
            methodology=raw.get("methodology"),
        )
        ok, _ = validate_poll(poll)
        if ok:
            out.append(poll)
    return out

class SourceMonitor:
    def __init__(self, source: dict[str, Any], session: requests.Session):
        self.source = source
        self.session = session

    def fetch(self) -> bytes:
        headers = {"User-Agent": "coalicion-poll-monitor/2.0 (+https://github.com/DrRomanSalvador/coalicion)"}
        method = self.source.get("method", "GET").upper()
        last_error = None
        for attempt in range(2):
            try:
                if method == "POST":
                    r = self.session.post(self.source["url"], data=self.source.get("data", {}),
                                          headers=headers, timeout=30)
                else:
                    r = self.session.get(self.source["url"], headers=headers, timeout=30)
                r.raise_for_status()
                return r.content
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
        raise last_error

    def parse(self, body: bytes) -> tuple[list[Poll], list[dict[str, Any]]]:
        kind = self.source.get("format", "page")
        if kind == "datoelectoral_html":
            return parse_dato_electoral(body, self.source), []
        if kind == "rss":
            return [], parse_rss_metadata(body, self.source)
        if kind == "electomania_json":
            return parse_electomania_json(body, self.source), []
        # Generic pages are monitored by cryptographic fingerprint only.
        return [], [{
            "discovery_id": hashlib.sha256(body).hexdigest(),
            "title": self.source.get("name", self.source["id"]),
            "link": self.source["url"],
            "publication_raw": "",
            "source_id": self.source["id"],
            "validation": "PAGE_FINGERPRINT_ONLY", "alertable": False,
        }]

class TwitterMonitor(SourceMonitor):
    def fetch(self) -> bytes:
        token = os.environ.get("X_BEARER_TOKEN")
        if not token:
            raise RuntimeError("X_BEARER_TOKEN_NOT_CONFIGURED")
        user_id = self.source.get("user_id")
        if not user_id:
            raise RuntimeError("X_USER_ID_NOT_CONFIGURED")
        r = self.session.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            params={"max_results": 10, "tweet.fields": "created_at,entities,text"},
            headers={"Authorization": f"Bearer {token}"}, timeout=20)
        r.raise_for_status()
        return r.content

class PollMonitor:
    def __init__(self, config_path: Path = CONFIG, state_path: Path = STATE):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.state_path = state_path
        self.state = self._load_state()
        self.session = requests.Session()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema":"POLL_MONITOR_STATE_V2","poll_hashes":{},
                    "discovery_hashes":{},"source_hashes":{},"failure_hashes":{},
                    "runs":0,"total_validated":0,"baseline_completed":False}
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        for key, default in {"poll_hashes": {}, "discovery_hashes": {}, "source_hashes": {}, "failure_hashes": {}, "runs": 0, "total_validated": 0, "baseline_completed": False}.items():
            state.setdefault(key, default)
        return state

    def _save_raw(self, source_id: str, body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()
        SURVEYS.mkdir(parents=True, exist_ok=True)
        path = SURVEYS / f"{source_id}__{digest}.raw"
        if not path.exists():
            path.write_bytes(body)
        return digest

    def fetch_all(self) -> tuple[list[Poll], list[dict[str, Any]], list[dict[str, Any]]]:
        polls: list[Poll] = []
        discoveries: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for source in self.config["sources"]:
            if source.get("optional") and (
                not os.environ.get("X_BEARER_TOKEN") or not source.get("user_id")
            ):
                continue
            try:
                monitor = TwitterMonitor(source, self.session) if source.get("format") == "twitter" else SourceMonitor(source, self.session)
                body = monitor.fetch()
                digest = self._save_raw(source["id"], body)
                self.state["source_hashes"][source["id"]] = digest
                self.state.setdefault("failure_hashes", {}).pop(source["id"], None)
                p, d = monitor.parse(body)
                polls.extend(p)
                for x in d:
                    x["source_hash"] = digest
                discoveries.extend(d)
            except Exception as exc:
                message = f"{type(exc).__name__}:{exc}"
                failures.append({"source_id":source["id"],"error":message})
        return polls, discoveries, failures

    def detect_new(self, polls: Iterable[Poll], discoveries: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        new, changed, new_discoveries = [], [], []
        for discovery in discoveries:
            key = f"{discovery['source_id']}::{discovery['discovery_id']}"
            fingerprint = hashlib.sha256(
                json.dumps(
                    {k: v for k, v in discovery.items() if k != "source_hash"},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            if self.state["discovery_hashes"].get(key) != fingerprint:
                self.state["discovery_hashes"][key] = fingerprint
                if discovery.get("alertable", False):
                    new_discoveries.append(discovery)
        for poll in polls:
            h = poll_hash(poll)
            old = self.state["poll_hashes"].get(poll.poll_id)
            self.state["poll_hashes"][poll.poll_id] = h
            event = {"poll":canonical_poll(poll),"poll_hash":h,"previous_poll_hash":old}
            if old is None:
                new.append(event)
            elif old != h:
                changed.append(event)
        return new, changed, new_discoveries

    def save(self, payload: dict[str, Any], *, meaningful: bool) -> Path | None:
        if not meaningful:
            return None
        SURVEYS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = SURVEYS / f"polls_{stamp}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self.state["total_validated"] = len(self.state["poll_hashes"])
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def alert(self, payload: dict[str, Any]) -> bool:
        events = payload["new_polls"] + payload["changed_polls"]
        discoveries = payload.get("discoveries", [])
        failures = payload["failures"]
        unsent_failures = []
        for failure in failures:
            key = hashlib.sha256(json.dumps(failure, sort_keys=True).encode()).hexdigest()
            if self.state.get("failure_hashes", {}).get(failure["source_id"]) != key:
                unsent_failures.append((failure, key))
        if not events and not discoveries and not unsent_failures:
            return False
        lines = ["🔔 Vigilancia electoral — actualización"]
        for d in discoveries[:10]:
            lines += ["", "🛰️ NUEVO DESCUBRIMIENTO", f"Fuente: {d['source_id']}",
                      f"Título: {d['title']}", f"Enlace: {d['link']}",
                      f"Estado: {d['validation']}"]
        for e in events[:10]:
            p = e["poll"]
            lines += ["", f"Estado: {'NUEVA' if e in payload['new_polls'] else 'CAMBIADA'}",
                      f"Fuente: {p['source_id']}", f"Encuestadora: {p['pollster']}",
                      f"Publicación: {p['publication_date']}",
                      "Estimaciones: " + ", ".join(f"{k} {v:g}%" for k,v in sorted(p["parties"].items()))]
        for f, key in unsent_failures[:10]:
            self.state.setdefault("failure_hashes", {})[f["source_id"]] = key
            lines += ["", f"⚠️ FUENTE BLOQUEADA: {f['source_id']}", f"Error: {f['error']}"]
        text = "\n".join(lines)[:4090]
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            print("Telegram no configurado; alerta registrada pero no enviada.")
            return False

        # Telegram identifies the conversation in every incoming message as
        # message.chat.id. Resolve the latest private conversation dynamically
        # so the bot replies to the person who actually started/talked to it,
        # without a hard-coded user/chat id.
        try:
            updates = self.session.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"limit": 100, "allowed_updates": json.dumps(["message"])},
                timeout=10,
            )
            updates.raise_for_status()
            update_items = updates.json().get("result", [])
        except requests.RequestException as exc:
            print(f"Telegram getUpdates error: {exc}", file=sys.stderr)
            return False

        candidates = []
        for update in update_items:
            message = update.get("message") or {}
            chat_info = message.get("chat") or {}
            sender = message.get("from") or {}
            if chat_info.get("type") != "private":
                continue
            if chat_info.get("id") is None or sender.get("id") is None:
                continue
            candidates.append({
                "update_id": int(update.get("update_id", 0)),
                "chat_id": int(chat_info["id"]),
                "user_id": int(sender["id"]),
                "username": sender.get("username"),
                "text": str(message.get("text") or "").strip(),
            })

        if not candidates:
            print(
                "Telegram: no hay conversación privada entrante; "
                "el usuario debe abrir el bot y enviar /start."
            )
            return False

        starts = [
            item for item in candidates
            if item["text"].split()[0:1] == ["/start"]
        ]
        selected = max(starts or candidates, key=lambda item: item["update_id"])
        chat_id = str(selected["chat_id"])

        print(
            "Telegram destination resolved from incoming message: "
            f"user_id={selected['user_id']} chat_id={chat_id} "
            f"username=@{selected['username'] or 'sin_username'}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        for attempt in range(2):
            try:
                r = self.session.post(
                    url,
                    json={"chat_id": chat_id, "text": text},
                    timeout=10,
                )
                r.raise_for_status()
                return True
            except requests.RequestException as exc:
                if attempt == 1:
                    print(f"Telegram error: {exc}", file=sys.stderr)
                else:
                    time.sleep(1)
        return False

    def run(self) -> dict[str, Any]:
        checked = datetime.now(timezone.utc).isoformat()
        baseline = not self.state.get("baseline_completed", False)
        polls, discoveries, failures = self.fetch_all()
        new, changed, new_discoveries = self.detect_new(polls, discoveries)
        if baseline:
            new, changed, new_discoveries = [], [], []
            self.state["baseline_completed"] = True
        payload = {
            "schema":"POLL_MONITOR_V2","checked_at":checked,
            "status":"BLOCKED" if failures else ("ALERT" if new or changed else "READY"),
            "found_polls":len(polls),"new_polls":new,"changed_polls":changed,
            "discoveries":new_discoveries,"failures":failures,
            "descriptive_only":True,
            "seat_projection":"BLOCKED_NO_TERRITORIAL_INPUT",
        }
        meaningful = baseline or bool(new or changed or new_discoveries or failures)
        path = self.save(payload, meaningful=meaningful)
        self.state["runs"] = int(self.state.get("runs", 0)) + 1
        self.state["last_run"] = checked
        self.state["last_status"] = payload["status"]
        self.state["last_new"] = len(new)
        self.state["last_changed"] = len(changed)
        self.state["last_discoveries"] = len(new_discoveries)
        self.state["last_failures"] = failures
        self.state["total_validated"] = len(self.state["poll_hashes"])
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Encontradas {len(polls)} encuestas validadas")
        print(f"{len(new)+len(changed)} encuestas nuevas/cambiadas")
        print(f"Guardado en {path}" if path else "Sin cambios persistibles.")
        self.alert(payload)
        # alert() may update failure deduplication state.
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload

if __name__ == "__main__":
    PollMonitor().run()
