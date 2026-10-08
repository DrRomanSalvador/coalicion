"""Generate and optionally send the COALICIÓN daily situation newsletter.

Sending is disabled unless SMTP credentials are explicitly configured.
Generation itself is deterministic from materialized repository evidence.
"""
from __future__ import annotations

import html
import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SURVEYS = ROOT / "data/surveys/current_2026/current_national.json"
OUTPUT = ROOT / "artifacts/newsletter/latest.html"


def load() -> dict:
    try:
        value = json.loads(SURVEYS.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_newsletter(data: dict | None = None) -> str:
    data = data if data is not None else load()
    surveys = [x for x in data.get("surveys", []) if isinstance(x, dict)]
    today = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y")
    rows = []
    for poll in surveys:
        shares = poll.get("shares", {})
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(poll.get('pollster', '—')))}</td>"
            f"<td>{html.escape(str(poll.get('publication_date', '—')))}</td>"
            f"<td>{shares.get('PP', '—')}%</td>"
            f"<td>{shares.get('PSOE', '—')}%</td>"
            f"<td>{shares.get('Vox', '—')}%</td>"
            f"<td>{shares.get('Sumar', '—')}%</td>"
            f"<td>{html.escape(str(poll.get('evidence_level', '—')))}</td>"
            "</tr>"
        )
    table = "".join(rows) or "<tr><td colspan='7'>NO DISPONIBLE</td></tr>"
    return f"""<!doctype html>
<html lang="es"><meta charset="utf-8">
<title>COALICIÓN — Sala de Situación {today}</title>
<h1>🧭 SALA DE SITUACIÓN — {today}</h1>
<p>Estado: <strong>demo no oficial</strong>. Los datos no verificados como primarios
se identifican explícitamente.</p>
<table border="1" cellpadding="6">
<thead><tr><th>Encuestadora</th><th>Publicación</th><th>PP</th><th>PSOE</th>
<th>Vox</th><th>Sumar</th><th>Evidencia</th></tr></thead>
<tbody>{table}</tbody></table>
<p><strong>Territorio:</strong> NO DISPONIBLE si no existe evidencia territorial
2026 suficiente. No se infieren observaciones territoriales desde una media nacional.</p>
<p>COALICIÓN — infraestructura neutral de auditoría y simulación reproducible.</p>
</html>"""


def write_newsletter() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_newsletter(), encoding="utf-8")
    return OUTPUT


def send_newsletter(recipient: str | None = None) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("NEWSLETTER_FROM", user).strip()
    recipient = (recipient or os.environ.get("NEWSLETTER_TO", "")).strip()
    if not all((host, user, password, sender, recipient)):
        return False
    msg = EmailMessage()
    msg["Subject"] = "🧭 COALICIÓN — Sala de Situación"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("Consulte la versión HTML de la Sala de Situación.")
    msg.add_alternative(build_newsletter(), subtype="html")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return True


if __name__ == "__main__":
    path = write_newsletter()
    print(path)
    if os.environ.get("NEWSLETTER_SEND", "").lower() == "true":
        if not send_newsletter():
            raise SystemExit("BLOCKED: SMTP credentials/recipient are not configured")
