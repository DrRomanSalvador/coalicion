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
                "has_job_permissions": bool(re.search(r"(?m)^\s{4}permissions:\s*$", block)),
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
        entries.append({
            "path": str(path.relative_to(ROOT)),
            "name": next((line.split(":", 1)[1].strip() for line in lines
                          if line.startswith("name:")), path.stem),
            "triggers": sorted(set(trigger_names)),
            "workflow_permissions_declared": bool(re.search(r"(?m)^permissions:\s*$", source)),
            "concurrency_declared": bool(re.search(r"(?m)^concurrency:\s*$", source)),
            "jobs": jobs,
            "jobs_without_timeout": [job["id"] for job in jobs if not job["has_timeout"]],
            "findings": findings,
        })

    payload = {
        "schema": "WORKFLOW_RESILIENCE_AUDIT_V1",
        "status": "PASS" if not read_errors and entries else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_count": len(entries),
        "counts": {
            "without_workflow_permissions": sum(not item["workflow_permissions_declared"] for item in entries),
            "without_concurrency": sum(not item["concurrency_declared"] for item in entries),
            "jobs_without_timeout": sum(len(item["jobs_without_timeout"]) for item in entries),
            "review_required_patterns": sum(len(item["findings"]) for item in entries),
        },
        "read_errors": read_errors,
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
                      "counts": payload["counts"], "output": str(OUTPUT.relative_to(ROOT)),
                      "read_errors": read_errors}, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
