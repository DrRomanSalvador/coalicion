"""Generate the concise COALICIÓN review briefing.

The generated HTML is an internal editorial draft. It is not sent automatically:
a human reviews, corrects and approves it before distribution.
"""
from __future__ import annotations

import html
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from src.situation_state import build_situation_state

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/newsletter/latest.html"


def _esc(value: object) -> str:
    return html.escape(str(value))


def build_newsletter() -> str:
    state = build_situation_state()
    changed = state["headline"]["changed"][:3]
    questions = state["headline"]["questions"][:3]
    uncertainties = state["headline"]["uncertainties"][:1]

    changes_html = "".join(
        f"<li><strong>{_esc(item.get('party', item.get('code', 'Cambio')))}</strong> "
        f"{_esc(item.get('summary', item.get('delta_pp', '')))}"
        f"{' (' + _esc(item.get('latest_poll_date')) + ')' if item.get('latest_poll_date') else ''}</li>"
        for item in changed
    ) or "<li>Sin cambio electoral materializado que pueda afirmarse con la evidencia disponible.</li>"

    questions_html = "".join(
        f"<li>{_esc(item['question'])}</li>" for item in questions
    ) or "<li>No hay preguntas prioritarias materializadas.</li>"

    uncertainty_html = "".join(
        f"<li>{_esc(item['statement'])}</li>" for item in uncertainties
    ) or "<li>No se ha materializado una incertidumbre adicional en este corte.</li>"

    radar = _esc(state["radar"])
    as_of = _esc(state["as_of"])
    return f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>COALICIÓN · Brief · {as_of}</title>
<style>
body{{margin:0;background:#f5f6f8;color:#111827;font-family:Arial,sans-serif}}
main{{max-width:680px;margin:0 auto;padding:28px 20px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:22px;margin:12px 0}}
h1{{font-size:25px;margin:0 0 4px}} h2{{font-size:14px;text-transform:uppercase;letter-spacing:.08em;margin:0 0 12px}}
li{{margin:9px 0;line-height:1.35}} .muted{{color:#6b7280;font-size:12px}}
.badge{{display:inline-block;border:1px solid #d1d5db;border-radius:999px;padding:4px 9px;font-size:11px}}
a{{color:#111827}}
</style></head>
<body><main>
<div class="card">
<h1>COALICIÓN · SALA DE SITUACIÓN</h1><div class="muted">Brief interno · {as_of}</div>
<p><span class="badge">RADAR: {radar}</span></p>
</div>
<div class="card"><h2>Encuestadora · Lo que cambió</h2><ol>{changes_html}</ol></div>
<div class="card"><h2>Preguntas de hoy</h2><ol>{questions_html}</ol></div>
<div class="card"><h2>Una incertidumbre</h2><ul>{uncertainty_html}</ul></div>
<div class="card">
<h2>Control</h2>
<p class="muted">Encuestas nacionales materializadas: {_esc(state['counts']['national_polls'])} ·
territoriales: {_esc(state['counts']['territorial_polls'])} ·
última publicación: {_esc(state['counts']['latest_poll_date'] or 'NO DISPONIBLE')}</p>
<p class="muted">Evidencia: {_esc(state['evidence']['input_hash'])}</p>
<p class="muted">Borrador editorial. Revisar y corroborar antes de distribuir.</p>
</div>
</main></body></html>"""


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
    msg["Subject"] = "COALICIÓN · Brief"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("Borrador de briefing generado por COALICIÓN; revisar antes de distribuir.")
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
