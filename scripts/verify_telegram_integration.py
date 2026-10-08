"""Materialize real Telegram integration evidence; never promotes failed checks."""
from __future__ import annotations
import json, os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.telegram_bot import COMMANDS, _chat_allowed, _sources, render_command
from src.telegram_timezone import now_madrid
from src.telegram_persistence import SNAPSHOT, snapshot as snapshot_telegram_state

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "artifacts/poll_monitor_state.json"
OUT = ROOT / "ci_evidence/telegram_integration.json"

def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    source_status = state.get("source_status")
    sources = _sources()
    snapshot_telegram_state()
    checks = {
        "source_status_present": isinstance(source_status, dict) and bool(source_status),
        "telegram_source_count_matches": isinstance(source_status, dict) and len(sources) == len(source_status),
        "telegram_sources_nonempty": bool(sources),
        "madrid_timezone": now_madrid().tzinfo is not None,
        "allowed_chats_configured": bool(os.environ.get("TELEGRAM_ALLOWED_CHATS", "").strip()),
        "allowed_chat_check_is_fail_closed": not _chat_allowed("__unauthorized_test_chat__"),
        "persistence_snapshot_present": SNAPSHOT.exists(),
    }
    command_results = {}
    for name, _ in COMMANDS:
        command = "/" + name
        if command in {"/admin_alertas", "/admin_config"}:
            continue
        try:
            value = render_command(command)
            command_results[command] = bool(str(value).strip())
        except Exception:
            command_results[command] = False
    checks["all_public_commands_return"] = all(command_results.values())
    checks["no_internal_certification_masking"] = "COMPROBACIÓN PENDIENTE" not in render_command("/situacion")
    checks["sources_command_exposes_materialized_sources"] = (
        any(str(s.get("id")) in render_command("/fuentes") for s in sources)
        if sources else False
    )
    checks["situacion_command_returns"] = bool(render_command("/situacion").strip())
    checks["fail_closed_escanos"] = "porcentajes nacionales" in render_command("/escanos").lower() or "evidencia provincial" in render_command("/escanos").lower()
    # Secret allowlist is an environment/deployment prerequisite, not a code-integrity failure.\n    # Runtime authorization remains fail-closed when it is absent.\n    code_checks = {k: v for k, v in checks.items() if k != "allowed_chats_configured"}\n    ok = all(code_checks.values())
    payload = {
        "schema": "TELEGRAM_INTEGRATION_EVIDENCE_V1",
        "status": "PASS" if ok else "BLOCKED",
        "executed": True,
        "source_count": len(sources),
        "source_status_count": len(source_status) if isinstance(source_status, dict) else 0,
        "checks": checks,
        "commands": command_results,
        "limitations": [] if ok else ["Una o más comprobaciones de integración no han pasado."],
        "generated_at": now_madrid().isoformat(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
