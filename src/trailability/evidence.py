"""Fail-closed evidence records for user-visible electoral values.

An evidence record is valid only when its primary URL, publication date,
fieldwork metadata and SHA-256 content/record hash are explicit. Secondary
replicas may be retained for discovery but cannot promote a value to primary.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Mapping


class EvidenceBlocked(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    primary_url: str
    publication_date: str
    fieldwork_start: str | None
    fieldwork_end: str | None
    sample_size: int | None
    methodology: str | None
    source_tier: str
    validation: str
    content_sha256: str
    record_sha256: str

    def validate(self) -> None:
        required = {
            "source_id": self.source_id,
            "primary_url": self.primary_url,
            "publication_date": self.publication_date,
            "content_sha256": self.content_sha256,
            "record_sha256": self.record_sha256,
        }
        missing = [k for k, v in required.items() if not str(v).strip()]
        if missing:
            raise EvidenceBlocked("MISSING_EVIDENCE:" + ",".join(missing))
        if not self.primary_url.startswith(("https://", "http://")):
            raise EvidenceBlocked("INVALID_PRIMARY_URL")
        if self.source_tier.startswith("PRIMARY") and self.validation not in {"PRIMARY_VERIFIED", "PRIMARY_VERIFIABLE"}:
            raise EvidenceBlocked("PRIMARY_VALIDATION_MISMATCH")
        if self.sample_size is not None and (type(self.sample_size) is not int or self.sample_size <= 0):
            raise EvidenceBlocked("INVALID_SAMPLE_SIZE")
        if len(self.content_sha256) != 64 or len(self.record_sha256) != 64:
            raise EvidenceBlocked("INVALID_SHA256")


def build_record(poll: Mapping[str, Any], *, content_sha256: str) -> dict[str, Any]:
    record = EvidenceRecord(
        source_id=str(poll.get("source_id", "")),
        primary_url=str(poll.get("primary_url", poll.get("source_url", ""))),
        publication_date=str(poll.get("publication_date", "")),
        fieldwork_start=poll.get("fieldwork_start"),
        fieldwork_end=poll.get("fieldwork_end"),
        sample_size=poll.get("sample_size"),
        methodology=poll.get("methodology"),
        source_tier=str(poll.get("source_tier", "")),
        validation=str(poll.get("validation", "")),
        content_sha256=content_sha256,
        record_sha256=canonical_hash({k: v for k, v in poll.items() if k not in {"record_sha256", "content_sha256"}} | {"content_sha256": content_sha256}),
    )
    record.validate()
    return asdict(record)


def validate_records(records: list[Mapping[str, Any]], *, require_primary: bool = False) -> dict[str, Any]:
    failures: list[str] = []
    primary = 0
    for index, item in enumerate(records):
        try:
            EvidenceRecord(**dict(item)).validate()
            if str(item.get("source_tier", "")).startswith("PRIMARY"):
                primary += 1
        except (TypeError, ValueError) as exc:
            failures.append(f"{index}:{exc}")
    if require_primary and primary == 0:
        failures.append("NO_PRIMARY_EVIDENCE")
    return {"status": "PASS" if not failures else "BLOCKED", "records": len(records), "primary_records": primary, "failures": failures, "fail_closed": True}
