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
    territorial: dict[str, dict[str, int]] | None = None
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
        "sample_size": poll.sample_size, "methodology": poll.methodology, "territorial": poll.territorial,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()

def canonical_poll(poll: Poll) -> dict[str, Any]:
    return asdict(poll)

def poll_identity(poll: Poll) -> str:
    """Stable study identity independent of mirror/source and published values."""
    payload = {
        "pollster": re.sub(r"\s+", " ", poll.pollster.strip().upper()),
        "publication_date": poll.publication_date,
        "fieldwork_start": poll.fieldwork_start,
        "fieldwork_end": poll.fieldwork_end,
        "sample_size": poll.sample_size,
        "methodology": poll.methodology,
    }
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()

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
    # Primary sources frequently omit minor parties or publish only the
    # principal candidates. Accept incomplete published tables, but only
    # when enough party-level evidence exists; never fill the residual mass.
    if len(values) >= 5 and total < 70:
        return False, f"PARTY_TOTAL_TOO_LOW:{total:.3f}"
    if total > 105:
        return False, f"PARTY_TOTAL_ABOVE_105:{total:.3f}"
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

def _extract_percentages(text: str) -> dict[str, float]:
    parties: dict[str, float] = {}
    party_patterns = {
        "PP": r"(?i)\b(?:PP|Partido Popular)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "PSOE": r"(?i)\bPSOE\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "VOX": r"(?i)\bVOX\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "SUMAR": r"(?i)\bSUMAR\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "PODEMOS": r"(?i)\bPODEMOS\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "ERC": r"(?i)\b(?:ERC|Esquerra(?: Republicana)?)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "JUNTS": r"(?i)\bJUNTS\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "PNV": r"(?i)\b(?:PNV|EAJ-PNV)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "EH BILDU": r"(?i)\b(?:EH BILDU|BILDU)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "BNG": r"(?i)\bBNG\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "CC": r"(?i)\b(?:CC|CCA)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "UPN": r"(?i)\bUPN\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        "SE ACABÓ LA FIESTA": r"(?i)\b(?:SALF|SE ACABÓ LA FIESTA)\b\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
    }
    for party, pattern in party_patterns.items():
        m = re.search(pattern, text)
        if m:
            parties[party] = float(m.group(1).replace(",", "."))
    return parties


def parse_national_html(body: bytes, source: dict[str, Any]) -> list[Poll]:
    """Extract a national-election poll only when the page itself states enough values.

    This deliberately rejects pages that merely discuss polls: at least five
    party estimates must be present and their total must be coherent.
    """
    soup = BeautifulSoup(body, "html.parser")
    text = soup.get_text(" ", strip=True)
    title = soup.title.get_text(" ", strip=True) if soup.title else source.get("name", source["id"])
    candidates = [text]
    for article in soup.find_all(["article", "main", "section"]):
        t = article.get_text(" ", strip=True)
        if t and len(t) > 200:
            candidates.append(t)
    best: tuple[dict[str, float], str] | None = None
    for candidate in candidates:
        if not re.search(r"(?i)(elecciones generales|estimación de voto nacional|barómetro nacional)", candidate):
            continue
        parties = _extract_percentages(candidate)
        if len(parties) >= 5:
            total = sum(parties.values())
            if 70 <= total <= 105 and (best is None or len(parties) > len(best[0])):
                best = (parties, candidate)
    if best is None:
        return []
    parties, evidence = best
    pub = None
    date_patterns = [
        r"(?i)\b(\d{1,2})\s*(?:de\s*)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(?:de\s*)?(2026)\b",
        r"\b(\d{1,2})[./-](\d{1,2})[./-](2026)\b",
    ]
    months = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
    for pat in date_patterns:
        m = re.search(pat, evidence)
        if m:
            if m.group(2).isdigit():
                pub = f"2026-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
            else:
                pub = f"2026-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
            break
    if not pub:
        return []
    sample = None
    sm = re.search(r"(?i)(?:muestra|entrevistas|encuestas|personas)\s*(?:de|:)?\s*([0-9][0-9.,]*)", evidence)
    if sm:
        sample = int(float(sm.group(1).replace(".", "").replace(",", ".")))
    pollster = source.get("pollster") or source.get("name") or source["id"]
    poll = Poll(
        poll_id=f"{source['id']}::{pub}::{title}",
        publication_date=pub, pollster=pollster, source_id=source["id"],
        source_url=source["url"], parties=parties, sample_size=sample,
    )
    return [poll] if validate_poll(poll)[0] else []


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
            territorial=raw.get("territorial"),
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
        headers = {"User-Agent": "coalicion-poll-monitor/2.1 (+https://github.com/DrRomanSalvador/coalicion)"}
        method = self.source.get("method", "GET").upper()
        urls = [self.source["url"], *self.source.get("alternate_urls", [])]
        errors = []
        for url in dict.fromkeys(urls):
            for attempt in range(2):
                try:
                    if method == "POST":
                        r = self.session.post(url, data=self.source.get("data", {}),
                                              headers=headers, timeout=30)
                    else:
                        r = self.session.get(url, headers=headers, timeout=30)
                    r.raise_for_status()
                    self.source["resolved_url"] = url
                    return r.content
                except requests.RequestException as exc:
                    errors.append(f"{url} => {type(exc).__name__}:{exc}")
                    if attempt == 0:
                        time.sleep(1)
        raise RuntimeError("SOURCE_FETCH_FAILED; " + " | ".join(errors[-4:]))

    def parse(self, body: bytes) -> tuple[list[Poll], list[dict[str, Any]]]:
        kind = self.source.get("format", "page")
        if kind == "datoelectoral_html":
            return parse_dato_electoral(body, self.source), []
        if kind == "rss":
            return [], parse_rss_metadata(body, self.source)
        if kind == "electomania_json":
            return parse_electomania_json(body, self.source), []
        if kind == "electomania_html":
            from .monitors.electomania_monitor import ElectomaniaMonitor
            return ElectomaniaMonitor(self.source, self.session).parse(body)
        if kind == "national_html":
            return parse_national_html(body, self.source), []
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
            return {"schema":"POLL_MONITOR_STATE_V3","poll_hashes":{},
                    "poll_identities":{},"discovery_hashes":{},"source_hashes":{},"failure_hashes":{},
                    "failure_streaks": {}, "failure_reported": {}, "recovered_sources": [], "poll_versions": {},
                    "runs":0,"total_validated":0,"baseline_completed":False}
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        # Migrate persisted state from V2 without discarding accumulated hashes.
        state["schema"] = "POLL_MONITOR_STATE_V3"
        for key, default in {"poll_hashes": {}, "poll_identities": {}, "discovery_hashes": {}, "source_hashes": {}, "failure_hashes": {}, "runs": 0, "total_validated": 0, "baseline_completed": False, "poll_versions": {}}.items():
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
            if source.get("disabled"):
                continue
            if source.get("optional") and source.get("format") == "twitter" and (
                not os.environ.get("X_BEARER_TOKEN") or not source.get("user_id")
            ):
                self.state.setdefault("source_status", {})[source["id"]] = {
                    "status": "SKIPPED_OPTIONAL",
                    "format": source.get("format", "page"),
                    "coverage_role": source.get("coverage_role", "optional"),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
                continue
            try:
                monitor = TwitterMonitor(source, self.session) if source.get("format") == "twitter" else SourceMonitor(source, self.session)
                body = monitor.fetch()
                digest = self._save_raw(source["id"], body)
                self.state["source_hashes"][source["id"]] = digest
                previous_streak = int(self.state.setdefault("failure_streaks", {}).get(source["id"], 0))
                if previous_streak >= 3 and self.state.setdefault("failure_reported", {}).get(source["id"]):
                    self.state.setdefault("recovered_sources", []).append({
                        "source_id": source["id"], "previous_streak": previous_streak,
                        "resolved_url": source.get("resolved_url", source["url"]),
                    })
                self.state.setdefault("failure_hashes", {}).pop(source["id"], None)
                self.state.setdefault("failure_streaks", {})[source["id"]] = 0
                self.state.setdefault("failure_reported", {}).pop(source["id"], None)
                self.state.setdefault("source_status", {})[source["id"]] = {
                    "status": "OK", "format": source.get("format", "page"),
                    "coverage_role": source.get("coverage_role", "primary"),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
                p, d = monitor.parse(body)
                polls.extend(p)
                for x in d:
                    x["source_hash"] = digest
                discoveries.extend(d)
            except Exception as exc:
                message = f"{type(exc).__name__}:{exc}"
                self.state.setdefault("source_status", {})[source["id"]] = {
                    "status": "FAILED", "format": source.get("format", "page"),
                    "coverage_role": source.get("coverage_role", "primary"),
                    "error": message, "checked_at": datetime.now(timezone.utc).isoformat(),
                }
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
        identities = self.state.setdefault("poll_identities", {})
        for poll in polls:
            h = poll_hash(poll)
            identity = poll_identity(poll)
            old = self.state["poll_hashes"].get(poll.poll_id)
            event = {"poll":canonical_poll(poll),"poll_hash":h,"previous_poll_hash":old,
                     "poll_identity":identity}
            if old is not None:
                self.state["poll_hashes"][poll.poll_id] = h
                identities[identity] = poll.poll_id
                if old != h:
                    event["event_type"] = "CORRECTION_OR_REPUBLICATION"
                    self.state.setdefault("poll_versions", {}).setdefault(poll.poll_id, []).append({
                        "poll_hash": h,
                        "previous_poll_hash": old,
                        "poll": canonical_poll(poll),
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                    })
                    changed.append(event)
                continue
            replica_of = identities.get(identity)
            if replica_of and replica_of != poll.poll_id:
                event["replica_of"] = replica_of
                self.state["poll_hashes"][poll.poll_id] = h
                continue
            self.state["poll_hashes"][poll.poll_id] = h
            identities[identity] = poll.poll_id
            event["event_type"] = "NEW"
            self.state.setdefault("poll_versions", {}).setdefault(poll.poll_id, []).append({
                "poll_hash": h,
                "previous_poll_hash": None,
                "poll": canonical_poll(poll),
                "captured_at": datetime.now(timezone.utc).isoformat(),
            })
            new.append(event)
        return new, changed, new_discoveries

    def audit_coverage(self, failures: list[dict[str, Any]], discoveries: list[dict[str, Any]]) -> dict[str, Any]:
        """Hard gate for the declared configured national universe."""
        sources = [s for s in self.config.get("sources", []) if not s.get("disabled")]
        blockers: list[str] = []
        statuses = self.state.get("source_status", {})
        failed_ids = {f["source_id"] for f in failures}
        structured = {"national_html", "datoelectoral_html", "electomania_json", "electomania_html"}
        for source in sources:
            sid = source["id"]
            if source.get("optional") and source.get("coverage_role") != "primary":
                continue
            # Discovery layers are coverage sensors, not primary evidence.
            # Their transport failures must be recorded but must not block the
            # national primary-source coverage gate.
            if source.get("coverage_role") == "primary" and (
                sid in failed_ids or statuses.get(sid, {}).get("status") != "OK"
            ):
                blockers.append(f"SOURCE_NOT_HEALTHY:{sid}")
            if source.get("coverage_role") == "primary" and source.get("format", "page") not in structured:
                blockers.append(f"PRIMARY_WITHOUT_STRUCTURED_EXTRACTOR:{sid}")
            if source.get("coverage_role") == "primary" and source.get("optional"):
                blockers.append(f"PRIMARY_CANNOT_BE_OPTIONAL:{sid}")
        # Discovery sensors are expected to produce non-canonical findings.
        # They are coverage evidence, not validated polls, so an unresolved
        # discovery must never be promoted to a data blocker merely because
        # the discovery layer observed a page change.
        unresolved = [
            d.get("discovery_id") for d in discoveries
            if d.get("validation") in {"UNVERIFIED", "PENDING", "DISCOVERY_ONLY"}
        ]
        if self.config.get("coverage_contract", {}).get("require_zero_unresolved_discoveries", True) and unresolved:
            blockers.append(f"UNRESOLVED_DISCOVERIES:{len(unresolved)}")
        unclassified = [s["id"] for s in sources if s.get("coverage_role") not in {"primary", "discovery", "optional"}]
        if unclassified:
            blockers.append("UNCLASSIFIED_SOURCES:" + ",".join(unclassified))
        total = not blockers
        return {
            "claim": "COBERTURA_TOTAL_VERIFICADA" if total else "COBERTURA_TOTAL_NO_VERIFICADA",
            "scope": self.config.get("coverage_contract", {}).get("scope", "configured_national_poll_universe"),
            "total": total,
            "sources_checked": len(sources),
            "primary_sources": sum(1 for s in sources if s.get("coverage_role") == "primary"),
            "discovery_sources": sum(1 for s in sources if s.get("coverage_role") == "discovery"),
            "blockers": blockers,
        }

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
        # Health alerts are actionable incidents, not per-run noise:
        # initial alert at 3 failures, reminder every 12 failures, recovery
        # only after a previously escalated outage actually recovers.
        unsent_failures = []
        recoveries = self.state.pop("recovered_sources", [])
        streaks = self.state.setdefault("failure_streaks", {})
        reported = self.state.setdefault("failure_reported", {})
        source_roles = {
            s["id"]: s.get("coverage_role", "discovery")
            for s in self.config.get("sources", [])
        }
        for failure in failures:
            sid = failure["source_id"]
            key = hashlib.sha256(json.dumps(failure, sort_keys=True).encode()).hexdigest()
            streaks[sid] = int(streaks.get(sid, 0)) + 1
            self.state.setdefault("failure_hashes", {})[sid] = key
            if source_roles.get(sid) == "primary" and streaks[sid] >= 3:
                if not reported.get(sid) or streaks[sid] % 12 == 0:
                    unsent_failures.append((failure, key, streaks[sid]))
        if not events and not discoveries and not unsent_failures and not recoveries:
            return False
        lines = ["🔔 Vigilancia electoral — actualización"]
        for d in discoveries[:10]:
            lines += ["", "🛰️ NUEVO DESCUBRIMIENTO", f"Fuente: {d['source_id']}",
                      f"Título: {d['title']}", f"Enlace: {d['link']}",
                      f"Estado: {d['validation']}"]
        for e in events[:10]:
            p = e["poll"]
            changed = e.get("event_type") == "CORRECTION_OR_REPUBLICATION"
            label = "CORRECCIÓN/REPUBLICACIÓN" if changed else "NUEVA"
            lines += ["", f"Estado: {label}",
                      f"Fuente: {p['source_id']}", f"Encuestadora: {p['pollster']}",
                      f"Publicación: {p['publication_date']}",
                      "Estimaciones: " + ", ".join(f"{k} {v:g}%" for k,v in sorted(p["parties"].items()))]
            versions = self.state.get("poll_versions", {}).get(p.get("poll_id"), [])
            previous = versions[-2].get("poll", {}).get("parties", {}) if changed and len(versions) >= 2 else {}
            if previous:
                deltas = []
                for party in sorted(set(p["parties"]) | set(previous)):
                    try:
                        delta = float(p["parties"].get(party, 0)) - float(previous.get(party, 0))
                    except (TypeError, ValueError):
                        continue
                    if abs(delta) >= 0.05:
                        deltas.append((abs(delta), party, delta))
                deltas.sort(reverse=True)
                if deltas:
                    lines.append("Cambios vs versión anterior: " + ", ".join(
                        f"{party} {delta:+.1f} pp" for _, party, delta in deltas[:6]
                    ))
                else:
                    lines.append("Cambios vs versión anterior: sin variación cuantificable.")
            elif changed:
                lines.append("Cambios: versión anterior no materializada; se conserva el evento sin inferir diferencias.")
        for f, key, streak in unsent_failures[:10]:
            self.state.setdefault("failure_reported", {})[f["source_id"]] = key
            lines += ["", f"⚠️ SALUD DE FUENTE: {f['source_id']}",
                      f"Incidencia persistente durante {streak} ejecuciones consecutivas.",
                      "Acción: revisar la ruta primaria/adaptador; no se sustituye por datos no verificados.",
                      f"Error: {f['error']}"]
        for recovery in recoveries[:10]:
            self.state.setdefault("failure_reported", {}).pop(recovery["source_id"], None)
            lines += ["", f"✅ FUENTE RECUPERADA: {recovery['source_id']}",
                      f"Había fallado {recovery['previous_streak']} ejecuciones consecutivas.",
                      f"Ruta operativa: {recovery['resolved_url']}"]
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
        coverage = self.audit_coverage(failures, discoveries)
        if baseline and coverage["total"]:
            self.state["baseline_completed"] = True
        if baseline:
            new, changed, new_discoveries = [], [], []
        payload = {
            "schema":"POLL_MONITOR_V3","checked_at":checked,
            "coverage": coverage,
            "status":"BLOCKED" if not coverage["total"] else ("ALERT" if new or changed else "READY"),
            "found_polls":len(polls),"validated_polls":[canonical_poll(p) for p in polls],"new_polls":new,"changed_polls":changed,
            "discoveries":new_discoveries,"failures":failures,
            "descriptive_only":True,
            "seat_projection":"BLOCKED_NO_TERRITORIAL_INPUT",
        }
        failure_notifications = []
        source_roles = {
            s["id"]: s.get("coverage_role", "discovery")
            for s in self.config.get("sources", [])
        }
        for failure in failures:
            sid = failure["source_id"]
            streak = int(self.state.get("failure_streaks", {}).get(sid, 0))
            key = hashlib.sha256(json.dumps(failure, sort_keys=True).encode()).hexdigest()
            if (
                source_roles.get(sid) == "primary"
                and streak >= 3
                and self.state.get("failure_reported", {}).get(sid) != key
            ):
                failure_notifications.append(failure)
        previous_coverage = self.state.get("last_coverage")
        coverage_changed = previous_coverage != coverage
        meaningful = baseline or bool(new or changed or new_discoveries or failure_notifications or coverage_changed)
        path = self.save(payload, meaningful=meaningful)
        self.state["runs"] = int(self.state.get("runs", 0)) + 1
        self.state["last_run"] = checked
        self.state["last_status"] = payload["status"]
        self.state["last_new"] = len(new)
        self.state["last_changed"] = len(changed)
        self.state["last_discoveries"] = len(new_discoveries)
        self.state["last_failures"] = failures
        self.state["last_coverage"] = coverage
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
