#!/usr/bin/env python3
"""Generate transparent DORA proxies from GitHub production deployments."""
from __future__ import annotations

import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "DrRomanSalvador/coalicion")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
WINDOW_DAYS = int(os.environ.get("DORA_WINDOW_DAYS", "30"))
OUT = Path(os.environ.get("DORA_OUTPUT_DIR", "artifacts/dora"))


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def api_get(path: str) -> Any:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN is required")
    url = path if path.startswith("https://") else f"{API}{path}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "coalicion-dora-metrics",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {detail}") from exc


def paginated(path: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        batch = api_get(f"{path}{separator}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError(f"Expected a list from GitHub API: {path}")
        result.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            return result
        page += 1
        if page > 20:
            raise RuntimeError(f"Pagination safety limit exceeded: {path}")


def enrich_deployments(raw: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=WINDOW_DAYS)
    commits: dict[str, datetime | None] = {}
    enriched = []
    for deployment in raw:
        if str(deployment.get("environment", "")).lower() != "production":
            continue
        created = parse_time(deployment.get("created_at"))
        if created is None or created < cutoff or created > now + timedelta(minutes=5):
            continue
        deployment_id = deployment.get("id")
        statuses = paginated(f"/repos/{REPO}/deployments/{deployment_id}/statuses")
        latest = max(statuses, key=lambda item: parse_time(item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc), default={})
        state = str(latest.get("state", "pending")).lower()
        sha = str(deployment.get("sha", ""))
        commit_at = None
        if sha:
            if sha not in commits:
                try:
                    commit_data = api_get(f"/repos/{REPO}/commits/{urllib.parse.quote(sha, safe='')}")
                    commit_at = parse_time(commit_data.get("commit", {}).get("committer", {}).get("date"))
                except (RuntimeError, AttributeError):
                    commit_at = None
                commits[sha] = commit_at
            commit_at = commits[sha]
        enriched.append({
            "id": deployment_id,
            "sha": sha or None,
            "created_at": created.isoformat(),
            "state": state,
            "status_at": latest.get("created_at"),
            "commit_at": commit_at.isoformat() if commit_at else None,
            "environment": "production",
        })
    return sorted(enriched, key=lambda item: item["created_at"])


def summarize(deployments: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    cutoff = now - timedelta(days=WINDOW_DAYS)
    successful = [d for d in deployments if d["state"] == "success"]
    terminal = [d for d in deployments if d["state"] in {"success", "failure", "error"}]
    failed = [d for d in terminal if d["state"] in {"failure", "error"}]
    lead_hours = []
    missing_commit_dates = 0
    for deployment in successful:
        deployed_at = parse_time(deployment.get("status_at")) or parse_time(deployment.get("created_at"))
        committed_at = parse_time(deployment.get("commit_at"))
        if deployed_at is None or committed_at is None:
            missing_commit_dates += 1
            continue
        delta = (deployed_at - committed_at).total_seconds() / 3600
        if delta >= 0:
            lead_hours.append(delta)
        else:
            missing_commit_dates += 1

    restore_hours = []
    ordered = sorted(deployments, key=lambda d: parse_time(d.get("status_at")) or parse_time(d.get("created_at")) or cutoff)
    for index, deployment in enumerate(ordered):
        if deployment["state"] not in {"failure", "error"}:
            continue
        failed_at = parse_time(deployment.get("status_at")) or parse_time(deployment.get("created_at"))
        if failed_at is None:
            continue
        recovery = next(
            (
                parse_time(candidate.get("status_at")) or parse_time(candidate.get("created_at"))
                for candidate in ordered[index + 1:]
                if candidate["state"] == "success"
                and (parse_time(candidate.get("status_at")) or parse_time(candidate.get("created_at"))) is not None
                and (parse_time(candidate.get("status_at")) or parse_time(candidate.get("created_at"))) >= failed_at
            ),
            None,
        )
        if recovery is not None:
            restore_hours.append((recovery - failed_at).total_seconds() / 3600)

    def stats(values: list[float]) -> dict[str, float | None]:
        return {
            "median_hours": round(statistics.median(values), 2) if values else None,
            "mean_hours": round(statistics.fmean(values), 2) if values else None,
            "sample_size": len(values),
        }

    return {
        "schema": "COALICION_DORA_METRICS_V1",
        "repository": REPO,
        "generated_at": now.isoformat(),
        "window_days": WINDOW_DAYS,
        "window_start": cutoff.isoformat(),
        "source": "GitHub Deployments API (environment=production)",
        "sample": {
            "production_deployments": len(deployments),
            "successful": len(successful),
            "failed_or_error": len(failed),
            "terminal": len(terminal),
            "pending_or_other": len(deployments) - len(terminal),
            "successful_without_commit_timestamp": missing_commit_dates,
        },
        "metrics": {
            "deployment_frequency": {
                "successful_deployments": len(successful),
                "per_day": round(len(successful) / WINDOW_DAYS, 4) if WINDOW_DAYS > 0 else None,
                "unit": "successful production deployments per day",
                "status": "MEASURED" if deployments else "INSUFFICIENT_DATA",
            },
            "lead_time_for_changes": {
                **stats(lead_hours),
                "unit": "hours from commit timestamp to successful deployment status",
                "status": "MEASURED" if lead_hours else "INSUFFICIENT_DATA",
            },
            "change_failure_rate": {
                "rate": round(len(failed) / len(terminal), 4) if terminal else None,
                "failed_deployments": len(failed),
                "terminal_deployments": len(terminal),
                "unit": "failed or errored terminal deployments / terminal deployments",
                "status": "MEASURED" if terminal else "INSUFFICIENT_DATA",
            },
            "time_to_restore": {
                **stats(restore_hours),
                "unit": "hours from failed deployment status to next successful deployment status",
                "status": "PROXY_MEASURED" if restore_hours else "INSUFFICIENT_DATA",
            },
        },
        "limitations": [
            "Requires real production deployments and statuses recorded through GitHub Deployments API.",
            "Lead time is commit-timestamp-to-deployment, not the full start-of-work-to-production interval.",
            "Change failure rate uses final deployment statuses as a proxy for user-impacting change failures.",
            "Time to restore is a proxy from deployment failure to next successful deployment; it is not incident-system MTTR.",
            "Missing observations are null/INSUFFICIENT_DATA, never fabricated zero values.",
        ],
        "deployments": deployments,
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    sample = report["sample"]
    cfr_rate = m["change_failure_rate"]["rate"]
    cfr_value = f"{cfr_rate * 100:.2f}%" if cfr_rate is not None else "INSUFFICIENT_DATA"
    lines = [
        "# COALICIÓN — DORA engineering metrics",
        "",
        f"- Repository: `{report['repository']}`",
        f"- Generated: {report['generated_at']}",
        f"- Window: {report['window_days']} days from {report['window_start']}",
        f"- Source: {report['source']}",
        f"- Production deployment records: {sample['production_deployments']}",
        "",
        "| Metric | Value | Status | Sample / definition |",
        "|---|---:|---|---|",
        f"| Deployment frequency | {m['deployment_frequency']['per_day'] if m['deployment_frequency']['per_day'] is not None else 'INSUFFICIENT_DATA'} per day | {m['deployment_frequency']['status']} | {m['deployment_frequency']['successful_deployments']} successful deployments |",
        f"| Lead time for changes | {m['lead_time_for_changes']['median_hours'] if m['lead_time_for_changes']['median_hours'] is not None else 'INSUFFICIENT_DATA'} h median | {m['lead_time_for_changes']['status']} | n={m['lead_time_for_changes']['sample_size']}; commit timestamp to deployment |",
        f"| Change failure rate | {cfr_value} | {m['change_failure_rate']['status']} | {m['change_failure_rate']['failed_deployments']}/{m['change_failure_rate']['terminal_deployments']} terminal deployments |",
        f"| Time to restore | {m['time_to_restore']['median_hours'] if m['time_to_restore']['median_hours'] is not None else 'INSUFFICIENT_DATA'} h median | {m['time_to_restore']['status']} | n={m['time_to_restore']['sample_size']}; deployment-based proxy |",
        "",
        "## Limitations",
    ]
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.extend(["", "## Deployment sample", "", "| ID | SHA | Created | Final state | Status timestamp |", "|---:|---|---|---|---|"])
    lines.extend(
        f"| {d['id']} | `{(d.get('sha') or '')[:12]}` | {d['created_at']} | {d['state']} | {d.get('status_at') or 'n/a'} |"
        for d in report["deployments"]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    if WINDOW_DAYS < 1 or WINDOW_DAYS > 365:
        raise RuntimeError("DORA_WINDOW_DAYS must be between 1 and 365")
    now = datetime.now(timezone.utc)
    raw = paginated(f"/repos/{REPO}/deployments?environment=production")
    deployments = enrich_deployments(raw, now)
    report = summarize(deployments, now)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dora_metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "dora_metrics.md").write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: DORA metrics could not be computed: {exc}", file=sys.stderr)
        raise SystemExit(1)
