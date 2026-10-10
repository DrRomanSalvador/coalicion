#!/usr/bin/env python3
"""Fail-closed GitHub Actions check gate for pull-request integration."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable


class GitHubAPIAuthError(RuntimeError):
    """Raised when GitHub rejects the workflow token or its permissions."""


class GitHubAPITransientError(RuntimeError):
    """Raised for a non-authentication API/CLI error that may be transient."""


def fetch_runs(
    repo: str,
    sha: str,
    current_run_id: str,
    runner: Callable[..., Any] = subprocess.run,
) -> list[dict[str, Any]]:
    """Fetch every run for the exact PR commit, classifying auth errors explicitly."""
    result = runner(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = "\n".join(
            part.strip()
            for part in (result.stderr or "", result.stdout or "")
            if part and part.strip()
        ) or f"gh api exited with status {result.returncode}"
        lowered = detail.lower()
        auth_status = re.search(r"\bhttp(?:\s+error)?\s*(401|403)\b", lowered)
        auth_phrase = any(
            marker in lowered
            for marker in (
                "bad credentials",
                "requires authentication",
                "resource not accessible by integration",
                "must have admin rights",
            )
        )
        if auth_status or auth_phrase:
            status = auth_status.group(1) if auth_status else "401/403"
            raise GitHubAPIAuthError(
                f"GitHub Actions API authentication/authorization failed (HTTP {status}). "
                "Verify GH_TOKEN validity, Actions read permission, and repository policy. "
                f"GitHub CLI detail: {detail}"
            )
        raise GitHubAPITransientError(f"GitHub Actions API request failed: {detail}")

    try:
        pages = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise GitHubAPITransientError(
            f"GitHub Actions API returned invalid JSON: {exc}"
        ) from exc
    if isinstance(pages, dict):
        pages = [pages]
    if not isinstance(pages, list):
        raise GitHubAPITransientError("GitHub Actions API response was not a page list")

    runs: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise GitHubAPITransientError("GitHub Actions API returned a malformed page")
        for run in page.get("workflow_runs", []):
            if not isinstance(run, dict) or run.get("head_sha") != sha:
                continue
            if str(run.get("id", "")) == current_run_id:
                continue
            runs.append(
                {
                    "id": run.get("id"),
                    "name": run.get("name", ""),
                    "status": run.get("status", ""),
                    "conclusion": run.get("conclusion"),
                    "run_number": run.get("run_number"),
                    "run_attempt": run.get("run_attempt"),
                    "created_at": run.get("created_at"),
                }
            )
    return latest_runs_per_workflow(runs)


def latest_runs_per_workflow(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use the newest attempt per workflow so obsolete failed attempts do not poison retries."""
    latest: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
    for run in runs:
        name = str(run.get("name") or run.get("id") or "unnamed")
        try:
            run_number = int(run.get("run_number") or 0)
            attempt = int(run.get("run_attempt") or 0)
            run_id = int(run.get("id") or 0)
        except (TypeError, ValueError):
            run_number, attempt, run_id = 0, 0, 0
        rank = (run_number, attempt, str(run.get("created_at") or ""), run_id)
        if name not in latest or rank > latest[name][0]:
            latest[name] = (rank, run)
    return [
        {
            "id": run.get("id"),
            "name": run.get("name", ""),
            "status": run.get("status", ""),
            "conclusion": run.get("conclusion"),
        }
        for _, run in latest.values()
    ]


REQUIRED_PR_SECTIONS = (
    "Causa raíz:",
    "Solución mínima:",
    "Principios afectados (01–25):",
    "Pruebas ejecutadas y resultado:",
    "CI del SHA exacto:",
    "Riesgo y rollback:",
    "Excepciones",
)


def validate_pr_body(body: str) -> list[str]:
    """Fail closed when a PR omits mandatory engineering evidence."""
    missing = [
        section
        for section in REQUIRED_PR_SECTIONS
        if section.casefold() not in body.casefold()
    ]

    heading = re.search(
        r"(?im)^[ \t]*(?:#{1,6}[ \t]+)?Principios afectados \(01–25\):[ \t]*(.*)$",
        body,
    )
    principle_text = ""
    if heading:
        following = body[heading.end():]
        next_heading = re.search(r"(?m)^[ \t]*#{1,6}[ \t]+\S", following)
        section_body = following[:next_heading.start()] if next_heading else following
        principle_text = "\n".join(
            part.strip()
            for part in (heading.group(1), section_body)
            if part and part.strip()
        ).strip()

    has_principle_ids = bool(re.search(r"(?<!\d)(?:0[1-9]|1\d|2[0-5])(?!\d)", principle_text))
    normalized = principle_text.casefold()
    justified_na = bool(
        re.search(r"\bn/?a\b", normalized)
        and re.search(r"\b(justificaci[oó]n|porque|motivo|no aplica|no son aplicables)\b", normalized)
        and len(re.sub(r"\bn/?a\b", "", normalized).strip(" \t\r\n-:;.")) >= 12
    )
    if not has_principle_ids and not justified_na:
        missing.append(
            "a populated list of applicable principles (01–25), or an explicit justified N/A"
        )
    return missing

def fetch_pr_body(
    repo: str,
    pr_number: str,
    runner: Callable[..., Any] = subprocess.run,
) -> str:
    result = runner(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".body // empty"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "unknown GitHub API error").strip()
        raise GitHubAPITransientError(f"Could not inspect PR description: {detail}")
    body = result.stdout.strip()
    if not body:
        raise GitHubAPITransientError("PR description is empty; mandatory engineering evidence is missing")
    return body


def fetch_changed_files(
    repo: str,
    pr_number: str,
    runner: Callable[..., Any] = subprocess.run,
) -> list[str]:
    """Fetch the complete PR file list; never guess which gates the change requires."""
    result = runner(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/pulls/{pr_number}/files?per_page=100",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "unknown GitHub API error").strip()
        raise GitHubAPITransientError(f"Could not inspect changed PR files: {detail}")
    try:
        pages = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise GitHubAPITransientError(f"GitHub returned invalid PR-file JSON: {exc}") from exc
    if isinstance(pages, dict):
        pages = [pages]
    if not isinstance(pages, list):
        raise GitHubAPITransientError("GitHub PR-file response was not a page list")
    filenames: set[str] = set()
    for page in pages:
        if isinstance(page, dict):
            page = [page]
        if not isinstance(page, list):
            raise GitHubAPITransientError("GitHub PR-file response contained a malformed page")
        for item in page:
            if isinstance(item, dict) and isinstance(item.get("filename"), str):
                filenames.add(item["filename"])
    if not filenames:
        raise GitHubAPITransientError("GitHub returned no changed files for the pull request")
    return sorted(filenames)


def required_checks_for_files(changed_files: list[str]) -> set[str]:
    """Select mandatory checks from the actual changed paths, not eventual API timing."""
    required = {
        "Methodology validation",
        "Methodology extensions validation",
        "Methodology integration",
        "Mandatory engineering contract",
        "Workflow resilience contract tests",
    }
    paths = [path.replace("\\", "/") for path in changed_files]
    product_prefixes = ("scripts/", "src/", "tests/", "data/", "config/")
    product_exact = {
        "run26.py", "requirements.txt", "requirements.lock", "pyproject.toml",
        ".github/workflows/product_pipeline.yml",
    }
    if any(path.startswith(product_prefixes) or path in product_exact for path in paths):
        required.add("Product pipeline 2026")
    exhaustive_prefixes = ("src/", "tests/", "scripts/", "config/", "data/", "artifacts/data/",
                           "docs/", "schemas/", "web/")
    if any(path.startswith(exhaustive_prefixes) or path.startswith(".github/workflows/")
           or path.endswith(".py") or path in {"requirements.txt", "requirements.lock",
                                                "pyproject.toml", "Dockerfile"} for path in paths):
        required.add("Exhaustive fail-closed validation")
    if any(path.startswith("telegram-worker/") or path in {
        ".github/workflows/telegram_worker_ci.yml",
        ".github/workflows/deploy_telegram_worker.yml",
    } for path in paths):
        required.add("Telegram Worker CI")
    dora_paths = {
        "scripts/dora_metrics.py", "tests/test_dora_metrics.py",
        ".github/workflows/dora-metrics.yml", ".github/workflows/deploy_telegram_worker.yml",
        "docs/DORA_METRICS.md",
    }
    if any(path in dora_paths for path in paths):
        required.add("DORA engineering metrics")
    return required


def main() -> int:
    repo = os.environ.get("GH_REPO", "").strip()
    sha = os.environ.get("HEAD_SHA", "").strip()
    current_run_id = os.environ.get("CURRENT_RUN_ID", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    missing = [
        name
        for name, value in (
            ("GH_REPO", repo),
            ("HEAD_SHA", sha),
            ("CURRENT_RUN_ID", current_run_id),
            ("PR_NUMBER", pr_number),
            ("GH_TOKEN", os.environ.get("GH_TOKEN", "").strip()),
        )
        if not value
    ]
    if missing:
        print(
            f"::error::Missing required integration-gate environment: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2

    try:
        pr_body = fetch_pr_body(repo, pr_number)
        missing_pr_evidence = validate_pr_body(pr_body)
        if missing_pr_evidence:
            print(
                "::error::PR is missing mandatory engineering evidence: "
                + json.dumps(missing_pr_evidence, ensure_ascii=False),
                file=sys.stderr,
                flush=True,
            )
            return 1
        changed_files = fetch_changed_files(repo, pr_number)
    except GitHubAPITransientError as exc:
        print(f"::error::{exc}", file=sys.stderr, flush=True)
        return 1
    required = required_checks_for_files(changed_files)
    print(
        "Required checks for changed files: "
        + json.dumps({"files": changed_files, "checks": sorted(required)}, sort_keys=True),
        flush=True,
    )
    # Product pipeline can run for 90 minutes; leave queue and stability margin.
    deadline = time.monotonic() + 110 * 60
    stable_signature = None
    stable_since = None

    while time.monotonic() < deadline:
        try:
            runs = fetch_runs(repo, sha, current_run_id)
        except GitHubAPIAuthError as exc:
            # Retrying a rejected credential cannot heal permissions; fail promptly.
            print(f"::error::{exc}", file=sys.stderr, flush=True)
            return 1
        except GitHubAPITransientError as exc:
            print(f"Waiting: GitHub Actions API temporarily unavailable: {exc}", flush=True)
            time.sleep(15)
            continue

        failed = [
            run
            for run in runs
            if run["status"] == "completed"
            and run["conclusion"] not in {"success", "skipped"}
        ]
        if failed:
            print(
                "Blocking merge: failed/cancelled check runs: "
                + json.dumps(failed, sort_keys=True),
                flush=True,
            )
            return 1

        pending = [run for run in runs if run["status"] != "completed"]
        completed_successfully = {
            run["name"]
            for run in runs
            if run["status"] == "completed" and run["conclusion"] == "success"
        }
        missing_success = sorted(required - completed_successfully)

        if not pending and not missing_success:
            signature = tuple(
                sorted(
                    (
                        str(run["id"]),
                        run["name"],
                        run["status"],
                        str(run["conclusion"]),
                    )
                    for run in runs
                )
            )
            now = time.monotonic()
            if signature != stable_signature:
                stable_signature = signature
                stable_since = now
            elif stable_since is not None and now - stable_since >= 30:
                print(
                    "All observed checks succeeded and the result stayed stable for 30 seconds. "
                    f"Checks={len(runs)}; revision={sha}",
                    flush=True,
                )
                break
        else:
            stable_signature = None
            stable_since = None
            print(
                f"Waiting for checks: pending={len(pending)} "
                f"missing_success={missing_success}",
                flush=True,
            )
        time.sleep(15)
    else:
        print(
            "Blocking merge: checks did not reach a stable all-green state within 110 minutes.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    # This workflow is a validation gate, not a merge authority. GitHub branch
    # protection must enforce required checks; never mutate the PR from this job.
    print(
        "All required checks succeeded and remained stable for 30 seconds. "
        f"Validated revision={sha}; integration may proceed only through repository branch protection.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
