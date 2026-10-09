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
                }
            )
    return runs


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

    required = {
        "Exhaustive fail-closed validation",
        "Methodology validation",
        "Methodology extensions validation",
        "Methodology integration",
        "Workflow resilience contract tests",
    }
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

    merge = subprocess.run(
        [
            "gh",
            "pr",
            "merge",
            pr_number,
            "--repo",
            repo,
            "--match-head-commit",
            sha,
            "--squash",
        ],
        check=False,
    )
    if merge.returncode:
        print(
            f"::error::GitHub refused PR #{pr_number} merge for verified SHA {sha} "
            f"(exit {merge.returncode}); branch protection was not bypassed.",
            file=sys.stderr,
            flush=True,
        )
        return merge.returncode
    print("Merged only after all observed checks and required validations passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
