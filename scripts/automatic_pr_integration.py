#!/usr/bin/env python3
"""Fail-closed GitHub Actions check gate for pull-request integration."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable


class GitHubAPIAuthError(RuntimeError):
    """Raised when GitHub rejects the workflow token or its permissions."""


class GitHubAPITransientError(RuntimeError):
    """Raised for a non-authentication API/CLI error that may be transient."""


def run_gh(
    args: list[str],
    runner: Callable[..., Any] = subprocess.run,
    context: str = "GitHub CLI request",
) -> Any:
    """Bound every GitHub CLI call so a stalled API cannot consume the full workflow timeout."""
    try:
        return runner(
            args,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitHubAPITransientError(f"{context} timed out after 30 seconds") from exc
    except OSError as exc:
        raise GitHubAPITransientError(f"{context} could not start: {exc}") from exc


def fetch_runs(
    repo: str,
    sha: str,
    current_run_id: str,
    runner: Callable[..., Any] = subprocess.run,
) -> list[dict[str, Any]]:
    """Fetch every run for the exact PR commit, classifying auth errors explicitly."""
    result = run_gh(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100",
        ],
        runner,
        "GitHub Actions run inventory",
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
    # Select the newest attempt before excluding this job. Otherwise an older
    # failed attempt of the same workflow can incorrectly block its own retry.
    latest = latest_runs_per_workflow(runs)
    return [run for run in latest if str(run.get("id", "")) != current_run_id]


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


def canonical_principle_titles() -> dict[int, str]:
    """Read the one canonical source of principle titles from the engineering charter."""
    charter = Path(__file__).resolve().parents[1] / "docs" / "ENGINEERING_CHARTER.md"
    try:
        content = charter.read_text(encoding="utf-8")
    except OSError as exc:
        raise GitHubAPITransientError(
            f"Cannot read canonical engineering charter at {charter}: {exc}"
        ) from exc
    titles: dict[int, str] = {}
    for match in re.finditer(r"(?m)^(\d{1,2})\. \*\*(.+?)\.\*\*", content):
        number = int(match.group(1))
        if 1 <= number <= 25:
            if number in titles:
                raise GitHubAPITransientError(
                    f"Canonical engineering charter defines principle {number:02d} more than once"
                )
            titles[number] = match.group(2).strip()
    if set(titles) != set(range(1, 26)):
        missing = sorted(set(range(1, 26)) - set(titles))
        raise GitHubAPITransientError(
            f"Canonical engineering charter must define all 25 numbered principles; missing={missing}"
        )
    return titles


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
    """Fail closed unless all required PR evidence and all 25 principles are substantive."""
    missing = [
        section
        for section in REQUIRED_PR_SECTIONS
        if section.casefold() not in body.casefold()
    ]

    # Presence of a label is not evidence. Require content for each section.
    for section in REQUIRED_PR_SECTIONS:
        heading = re.search(
            rf"(?im)^[ \t]*(?:#{{1,6}}[ \t]+)?{re.escape(section)}[ \t]*(.*)$",
            body,
        )
        if not heading:
            continue
        following = body[heading.end():]
        next_heading = re.search(r"(?m)^[ \t]*#{{1,6}}[ \t]+\S", following)
        section_body = following[:next_heading.start()] if next_heading else following
        if section == "Principios afectados (01–25):":
            continue  # Validated in detail below, one disposition per canonical principle.
        evidence = " ".join((heading.group(1), section_body))
        evidence = re.sub(r"(?m)^[ \t]*(?:[-*]|\d+\.)[ \t]*", " ", evidence)
        evidence = re.sub(r"[#*_\`>]", "", evidence).strip()
        if len(evidence) < 10:
            missing.append(f"section {section!r} is present but has no substantive evidence")

    heading = re.search(
        r"(?im)^[ \t]*(?:#{{1,6}}[ \t]+)?Principios afectados \\(01–25\\):[ \t]*(.*)$",
        body,
    )
    principle_text = ""
    if heading:
        following = body[heading.end():]
        next_heading = re.search(r"(?m)^[ \t]*#{{1,6}}[ \t]+\S", following)
        section_body = following[:next_heading.start()] if next_heading else following
        principle_text = "\\n".join(
            part.strip()
            for part in (heading.group(1), section_body)
            if part and part.strip()
        ).strip()

    titles = canonical_principle_titles()
    dispositions: dict[int, tuple[str, str]] = {{}}
    for line in principle_text.splitlines():
        match = re.match(
            r"^\\s*(?:[-*]\\s*)?(?:\\*\\*)?(0[1-9]|1[0-9]|2[0-5])(?:\\*\\*)?\\s+"
            r"(APLICA|N/A|NO APLICA)\\b\\s*[:—-]?\\s*(.*?)\\s*$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        number = int(match.group(1))
        disposition = match.group(2).upper()
        rationale = re.sub(r"[*_]", "", match.group(3)).strip()
        canonical_title = titles[number]
        if not rationale.casefold().startswith(canonical_title.casefold()):
            missing.append(
                f"principle {{number:02d}} must name its canonical title: {{canonical_title}}"
            )
            continue
        if number in dispositions:
            missing.append(f"principle {{number:02d}} is declared more than once")
            continue
        explanation = rationale[len(canonical_title):].strip(" \\t:—-")
        if len(explanation) < 20:
            missing.append(f"principle {{number:02d}} needs a concrete rationale after its canonical title (at least 20 characters)")
            continue
        if disposition in {{"N/A", "NO APLICA"}} and not re.search(
            r"\\b(porque|motivo|justificaci[oó]n|no modifica|no afecta|no cambia|no corresponde|fuera de alcance)\\b",
            rationale,
            flags=re.IGNORECASE,
        ):
            missing.append(f"principle {{number:02d}} is N/A without an explicit justification")
            continue
        dispositions[number] = (disposition, rationale)

    for number in range(1, 26):
        if number not in dispositions:
            missing.append(
                f"principle {{number:02d}} must have exactly one APLICA/N/A disposition and a concrete rationale"
            )
    return missing

def fetch_current_pr_head_sha(
    repo: str,
    pr_number: str,
    runner: Callable[..., Any] = subprocess.run,
) -> str:
    """Read the live PR head so an old validation run never merges a superseded SHA."""
    result = run_gh(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha"],
        runner,
        "Live PR head lookup",
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "unknown GitHub API error").strip()
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
                f"GitHub PR-head API authentication/authorization failed (HTTP {status}). "
                "Verify GH_TOKEN validity, pull-requests read permission, and repository policy. "
                f"GitHub CLI detail: {detail}"
            )
        raise GitHubAPITransientError(f"Could not verify current PR head: {detail}")
    current_sha = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", current_sha):
        raise GitHubAPITransientError("GitHub returned an empty or malformed current PR head SHA")
    return current_sha


def fetch_pr_body(
    repo: str,
    pr_number: str,
    runner: Callable[..., Any] = subprocess.run,
) -> str:
    result = run_gh(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".body // empty"],
        runner,
        "PR evidence lookup",
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "unknown GitHub API error").strip()
        raise GitHubAPITransientError(f"Could not inspect PR description: {detail}")
    # An empty body is valid API data but invalid PR evidence; let the validator
    # reject it explicitly instead of retrying a permanent user edit as a transient error.
    return result.stdout.strip()


def fetch_changed_files(
    repo: str,
    pr_number: str,
    runner: Callable[..., Any] = subprocess.run,
) -> list[str]:
    """Fetch the complete PR file list; never guess which gates the change requires."""
    result = run_gh(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/pulls/{pr_number}/files?per_page=100",
        ],
        runner,
        "Changed PR file inventory",
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
        "Repository-wide self-regulation",
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

    colmena_hf_paths = {
        "scripts/colmena_queen_hf.py", "scripts/colmena_agent_hf.py",
        "tests/test_colmena_hf_agents.py", "docs/COLMENA_MISSION_CONTROL.json",
        ".github/workflows/colmena_hf_agents.yml", ".github/workflows/colmena_hf_tests.yml",
    }
    if any(path in colmena_hf_paths for path in paths):
        required.add("Colmena HF — tests aislados")

    demo_multiparty_paths = {
        "scripts/demo_multiparty.py", "config/demo_multiparty_2023.json",
        "artifacts/demo_multiparty_2023.json", "artifacts/data/election_2023_canonical.json",
        "src/electoral.py", "src/coalition.py", "scripts/demo_e2e.py",
        "scripts/demo_decision_analysis.py", "scripts/demo_decision_server.py",
        "tests/test_demo_decision_server.py", "tests/test_demo_deployment_config.py",
        "render.yaml", "tests/test_demo_decision_analysis.py", "web/demo/index.html",
        "tests/test_demo_decision_ui.py", "tests/test_demo_multiparty.py",
        "tests/test_demo_e2e.py", ".github/workflows/demo-multiparty.yml",
    }
    if any(path in demo_multiparty_paths for path in paths):
        required.add("Demo multiparty 2023")

    if any(path in {
        "scripts/ingest_official_electoral_history.R",
        ".github/workflows/inspect-interior-source.yml",
    } for path in paths):
        required.add("Inspect official Interior download transport")

    mvp_paths = {
        "tests/test_mvp_e2e.py", "tests/test_data_collection.py",
        "tests/test_full_pipeline.py", "src/data.py", "scripts/materialize_current_surveys.py",
        "api.py", "requirements.txt", "requirements.lock", "render.yaml",
        ".github/workflows/mvp-validation.yml",
    }
    if any(path in mvp_paths or path.startswith((
        "src/web/", "src/email/", "src/pipeline/", "data/surveys/current_2026/",
    )) for path in paths):
        required.add("mvp-validation")

    seec_production_paths = {
        "scripts/run_seec_production.py", "src/seec_bayesian.py",
        "src/reproducibility_contract.py", "artifacts/data/cis_historical_2004_2023.csv",
        "artifacts/data/cis_recent_2024_2026.csv", "requirements.txt",
        ".github/workflows/seec-production-real.yml",
    }
    if any(path in seec_production_paths for path in paths):
        required.add("SEEC production real")

    telegram_bot_paths = {
        "src/telegram_bot.py", "tests/test_telegram_bot.py", "requirements.txt",
    }
    if any(path in telegram_bot_paths for path in paths):
        required.add("Telegram bot validation")

    unlock_paths = {
        "scripts/complete_historical_calibration.py", "scripts/run_mc_10000.py",
        "scripts/materialize_seec_posterior.py", "src/oos_pipeline.py",
        "src/reproducibility_contract.py", "data/resultados_oficiales_2004_2023.csv",
        "artifacts/data/election_2023_canonical.json", "requirements.txt",
        ".github/workflows/unlock-verification.yml",
    }
    if any(path in unlock_paths for path in paths):
        required.add("Unlock verification")
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
            current_head_sha = fetch_current_pr_head_sha(repo, pr_number)
            if current_head_sha != sha:
                print(
                    "::notice::PR head changed while this gate was waiting; "
                    "this stale validation exits without requesting a merge.",
                    flush=True,
                )
                return 0
            current_body = fetch_pr_body(repo, pr_number)
            if current_body != pr_body:
                print(
                    "::notice::PR evidence body changed while this gate was waiting; "
                    "this stale validation exits without requesting a merge.",
                    flush=True,
                )
                return 0
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

    # Ask GitHub to queue the squash merge for this exact validated revision.
    # GitHub still enforces every required check, review, signature, and branch rule.
    print(
        "All required checks succeeded and remained stable for 30 seconds. "
        f"Requesting protected auto-squash merge for revision={sha}.",
        flush=True,
    )
    try:
        merge = subprocess.run(
            ["gh", "pr", "merge", pr_number, "--auto", "--squash", "--match-head-commit", sha],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print(
            "::error::GitHub auto-merge request timed out after 30 seconds; no merge success is assumed.",
            file=sys.stderr,
            flush=True,
        )
        return 1
    if merge.returncode:
        detail = "\n".join(
            part.strip()
            for part in (merge.stderr or "", merge.stdout or "")
            if part and part.strip()
        ) or f"gh pr merge exited with status {merge.returncode}"
        print(
            "::error::Could not enable protected auto-merge. "
            "Check repository auto-merge settings, token permissions, and branch rules. "
            + detail,
            file=sys.stderr,
            flush=True,
        )
        return 1
    print(
        "GitHub accepted the auto-squash merge request. The platform will merge only "
        "after all branch protection requirements are satisfied.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
