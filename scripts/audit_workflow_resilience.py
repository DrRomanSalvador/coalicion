#!/usr/bin/env python3
"""Inventory GitHub Actions resilience risks without guessing that every pattern is a defect.

Findings are advisory and include source lines so a human/agent can review each case.
The audit fails only when workflow files are absent or unreadable; it never silently
converts heuristic findings into a false certification.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
OUTPUT = ROOT / "artifacts" / "verification" / "workflow_resilience_audit.json"

TRIGGERS = {
    "push", "pull_request", "pull_request_target", "workflow_dispatch", "schedule",
    "workflow_run", "repository_dispatch", "issues", "issue_comment", "workflow_call",
    "merge_group", "release", "workflow_dispatch",
}
REVIEW_PATTERNS = {
    "continue_on_error": re.compile(r"^\s*continue-on-error:\s*true\s*$"),
    "shell_error_suppression": re.compile(r"\|\|\s*true\b"),
    "manual_error_mode": re.compile(r"^\s*set\s+\+e\s*$"),
    "direct_git_push": re.compile(r"\bgit\s+push\b"),
    "always_condition": re.compile(r"^\s*if:\s*always\(\)\s*$"),
    "cancels_in_progress": re.compile(r"^\s*cancel-in-progress:\s*true\s*$"),
    "privileged_pull_request_target": re.compile(r"^\s*pull_request_target:\s*$"),
    "mutable_action_ref": re.compile(r"^\s*uses:\s+[^\s]+@(main|master)\s*$"),
}


def permission_declarations(source: str) -> tuple[bool, bool]:
    """Return (workflow-level, job-level) permission declarations, including inline maps."""
    workflow_level = bool(re.search(r"(?m)^permissions:\s*(?:\{[^}]*\})?\s*(?:#.*)?$", source))
    job_level = bool(re.search(r"(?m)^    permissions:\s*(?:\{[^}]*\})?\s*(?:#.*)?$", source))
    return workflow_level, job_level


def audit_self_healer_contract(source: str) -> list[str]:
    """Return missing fail-safe recovery contracts; pagination regressions are blocking."""
    checks = {
        "query is paginated and scoped to current main SHA": 'gh api --paginate --slurp "repos/$REPOSITORY/actions/runs?head_sha=$main_sha&per_page=100"',
        "self-healer excludes its own workflow": "select(.workflow_id != $self_id)",
        "only completed runs below the retry budget on current main are eligible": 'select(.status == "completed" and .run_attempt < 3)',
        "attempt number is rechecked before rerun": "run_attempt=",
        "stale or over-budget candidates are skipped": '[[ "$status" == "completed" && "$run_sha" == "$main_sha" && "$run_attempt" -lt "$max_attempts" ]] || continue',
        "only current main branch/SHA is eligible": 'select(.head_branch == "main" and .head_sha == $sha)',
        "each sweep caps successful reruns and candidate attempts": '[[ "$count" -lt 5 && "$attempted" -lt 25 ]]',
        "older candidates are processed first": "sort_by(.created_at)",
        "individual request errors are recorded": "RERUN_REQUEST_FAILED",
        "exhausted retry budget is surfaced even with other candidates": "EXHAUSTED_RETRY_BUDGET",
        "cancelled runs use a full rerun": 'gh run rerun "$run_id" --repo "$REPOSITORY"',
        "failed runs retry failed jobs only": 'gh run rerun "$run_id" --failed --repo "$REPOSITORY"',
        "manual path rejects active runs": "queued|in_progress|waiting|requested|pending",
        "manual path rejects unknown run states": "unknown status",
    }
    return [label for label, literal in checks.items() if literal not in source]


def audit_product_release_persistence(source: str) -> list[str]:
    """Require a fresh-main check before persisting release evidence."""
    checks = {
        "release writer uses strict shell mode": "set -euo pipefail",
        "release writer fetches main before publishing": "git fetch origin main",
        "release writer compares main to the tested SHA": '[[ "$remote_sha" != "$GITHUB_SHA" ]]',
        "stale evidence is skipped instead of pushed": "refusing to publish stale product gate output",
        "push failures are rechecked against current main": "Product release evidence push failed while main still matches the tested commit.",
    }
    return [label for label, literal in checks.items() if literal not in source]


def writer_without_concurrency(source: str) -> bool:
    """Detect workflows that push commits but do not serialize writers."""
    pushes = bool(re.search(r"(?m)^ *if +git push|^ *git push", source))
    serialized = bool(re.search(r"(?m)^concurrency:", source))
    return pushes and not serialized


def audit_telegram_pages_contract(source: str) -> list[str]:
    """Require safe Pages deployment and an honest non-failing skip when setup is unavailable."""
    checks = {
        "workflow declares Pages deployment permissions": "pages: write",
        "workflow declares OIDC deployment permission": "id-token: write",
        "deployment checks Pages setup before configure-pages": "Preflight GitHub Pages configuration",
        "first-time enablement prefers an explicit admin token": "secrets.PAGES_ADMIN_TOKEN || github.token",
        "workflow enables Pages when authorized": "enablement: true",
        "workflow publishes the Mini App artifact": "actions/upload-pages-artifact@v3",
        "workflow deploys the artifact": "actions/deploy-pages@v4",
        "missing permission is handled without falsely reporting deployment": "deploy_enabled=false",
        "missing permission has an actionable diagnostic": "Enable Pages once in Settings > Pages",
        "Pages-dependent steps are skipped when unavailable": "if: steps.preflight.outputs.deploy_enabled == 'true'",
    }
    return [label for label, literal in checks.items() if literal not in source]


def main() -> int:
    if not WORKFLOWS.is_dir():
        print(f"FAIL: missing workflow directory: {WORKFLOWS}", file=sys.stderr)
        return 2
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not paths:
        print("FAIL: no GitHub Actions workflow files found", file=sys.stderr)
        return 2

    entries = []
    read_errors = []
    critical_findings = []
    healer_seen = False
    pages_seen = False
    product_release_seen = False
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            read_errors.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
            continue
        lines = source.splitlines()
        trigger_names = []
        in_on = False
        for line in lines:
            if line == "on:":
                in_on = True
                continue
            if in_on and line and not line[0].isspace():
                in_on = False
            if in_on:
                match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*$", line)
                if match and match.group(1) in TRIGGERS:
                    trigger_names.append(match.group(1))

        jobs_section = source.split("jobs:", 1)[1] if "jobs:" in source else ""
        job_matches = list(re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", jobs_section))
        jobs = []
        for index, match in enumerate(job_matches):
            end = job_matches[index + 1].start() if index + 1 < len(job_matches) else len(jobs_section)
            block = jobs_section[match.start():end]
            jobs.append({
                "id": match.group(1),
                "has_timeout": bool(re.search(r"(?m)^\s+timeout-minutes:\s*\d+\s*$", block)),
                "has_job_permissions": bool(re.search(r"(?m)^ {4}permissions:", block)),
            })

        findings = []
        for line_no, line in enumerate(lines, start=1):
            for rule, pattern in REVIEW_PATTERNS.items():
                if pattern.search(line):
                    findings.append({
                        "rule": rule,
                        "line": line_no,
                        "text": line.strip()[:240],
                        "classification": "REVIEW_REQUIRED",
                    })
        relative_path = str(path.relative_to(ROOT))
        if relative_path == ".github/workflows/autonomous_self_healer.yml":
            healer_seen = True
            missing_contracts = audit_self_healer_contract(source)
            if missing_contracts:
                critical_findings.extend(
                    {"path": relative_path, "missing_contract": item}
                    for item in missing_contracts
                )
        if relative_path == ".github/workflows/telegram_miniapp.yml":
            pages_seen = True
            missing_contracts = audit_telegram_pages_contract(source)
            if missing_contracts:
                critical_findings.extend(
                    {"path": relative_path, "missing_contract": item}
                    for item in missing_contracts
                )
        if relative_path == ".github/workflows/product_release.yml":
            product_release_seen = True
            missing_contracts = audit_product_release_persistence(source)
            if missing_contracts:
                critical_findings.extend(
                    {"path": relative_path, "missing_contract": item}
                    for item in missing_contracts
                )
        if writer_without_concurrency(source):
            critical_findings.append({
                "path": relative_path,
                "missing_contract": "workflow commits to a remote branch without top-level concurrency serialization",
            })

        workflow_permissions, job_permissions = permission_declarations(source)

        entries.append({
            "path": relative_path,
            "name": next((line.split(":", 1)[1].strip() for line in lines
                          if line.startswith("name:")), path.stem),
            "triggers": sorted(set(trigger_names)),
            "workflow_permissions_declared": workflow_permissions,
            "job_permissions_declared": job_permissions,
            "permissions_declared": workflow_permissions or job_permissions,
            "concurrency_declared": bool(re.search(r"(?m)^concurrency:\s*$", source)),
            "jobs": jobs,
            "jobs_without_timeout": [job["id"] for job in jobs if not job["has_timeout"]],
            "findings": findings,
        })

    for entry in entries:
        if not entry["permissions_declared"]:
            critical_findings.append({"path": entry["path"], "missing_contract": "no workflow-level or job-level permissions declaration"})
        if not entry["concurrency_declared"]:
            critical_findings.append({"path": entry["path"], "missing_contract": "no concurrency group"})
        for job_id in entry["jobs_without_timeout"]:
            critical_findings.append({"path": entry["path"], "missing_contract": f"job {job_id} has no timeout-minutes"})

    if not healer_seen:
        critical_findings.append({"path": ".github/workflows/autonomous_self_healer.yml", "missing_contract": "self-healer workflow is missing"})
    if not pages_seen:
        critical_findings.append({"path": ".github/workflows/telegram_miniapp.yml", "missing_contract": "Telegram Pages deployment workflow is missing"})
    if not product_release_seen:
        critical_findings.append({"path": ".github/workflows/product_release.yml", "missing_contract": "product release gate workflow is missing"})

    payload = {
        "schema": "WORKFLOW_RESILIENCE_AUDIT_V1",
        "status": "PASS" if not read_errors and entries and not critical_findings else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_count": len(entries),
        "counts": {
            "without_workflow_permissions": sum(not item["workflow_permissions_declared"] for item in entries),
            "without_any_permissions": sum(not item["permissions_declared"] for item in entries),
            "without_concurrency": sum(not item["concurrency_declared"] for item in entries),
            "jobs_without_timeout": sum(len(item["jobs_without_timeout"]) for item in entries),
            "review_required_patterns": sum(len(item["findings"]) for item in entries),
        },
        "read_errors": read_errors,
        "critical_findings": critical_findings,
        "workflows": entries,
        "limitations": [
            "Pattern matches are review prompts, not automatic proof of a defect.",
            "Static inspection does not execute workflows or validate remote service behavior.",
            "YAML syntax and expression validation remain the responsibility of actionlint/CI.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "workflow_count": payload["workflow_count"],
                      "counts": payload["counts"], "critical_findings": len(critical_findings), "output": str(OUTPUT.relative_to(ROOT)),
                      "read_errors": read_errors}, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
