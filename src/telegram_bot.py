"""Neutral Telegram command bot for the canonical COALICIÓN pipeline."""
from __future__ import annotations
import json
import os
import time
from datetime import date
from pathlib import Path
from typing import Any
import requests

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"artifacts/poll_monitor_state.json"
OBSERVATIONS=ROOT/"artifacts/estimation/observations.json"
ESTIMATION=ROOT/"artifacts/estimation/real_estimation.json"
SNAPSHOT=ROOT/"artifacts/decision_snapshot.json"
API_TIMEOUT=20
API_RETRIES=4

class TelegramBotError(RuntimeError):
    pass

def _token() -> str:
    token=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
    if not token or token=="TU_TOKEN_AQUI":
        raise TelegramBotError("TELEGRAM_BOT_TOKEN is required")
    return token

def _api(method:str,**kwargs:Any)->dict[str,Any]:
    last:Exception|None=None
    for attempt in range(API_RETRIES):
        try:
            response=requests.post(
                f"https://api.telegram.org/bot{_token()}/{method}",
                timeout=API_TIMEOUT,
                **kwargs,
            )
            response.raise_for_status()
            payload=response.json()
            if not payload.get("ok"):
                raise TelegramBotError(f"Telegram API error: {payload}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last=exc
            if attempt + 1 < API_RETRIES:
                time.sleep(min(2 ** attempt, 8))
    raise TelegramBotError(f"Telegram transport failed after {API_RETRIES} attempts: {last}") from last

def send_message(chat_id:int,text:str)->None:
    _api("sendMessage",json={"chat_id":chat_id,"text":text[:4090]})

def _load_json(path:Path)->dict[str,Any]|None:
    if not path.exists(): return None
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return None
    return value if isinstance(value,dict) else None

def _observations()->dict[str,Any]:
    return _load_json(OBSERVATIONS) or {}

def _latest_polls()->list[dict[str,Any]]:
    obs=_observations()
    rows=obs.get("polls") or []
    if isinstance(rows,list) and rows: return [x for x in rows if isinstance(x,dict)]
    state=_load_json(STATE) or {}
    rows=state.get("validated_polls") or state.get("polls") or []
    return [x for x in rows if isinstance(x,dict)] if isinstance(rows,list) else []

def _fmt_delta(current:dict[str,Any],previous:dict[str,Any],party:str)->str:
    try:
        d=float(current.get(party,0))-float(previous.get(party,0))
        return f"{d:+.1f} pp"
    except (TypeError,ValueError): return "n/d"

def _prediction_text()->str:
    estimation=_load_json(ESTIMATION)
    snapshot=_load_json(SNAPSHOT)
    if estimation and estimation.get("status")=="BLOCKED":
        return (
            "PREDICCIÓN: BLOQUEADA\n"
            "Motivo: no existe una observación territorial explícita para las 52 circunscripciones.\n"
            f"Sondeos nacionales observados: {estimation.get('national_poll_count',0)}\n"
            f"Observaciones territoriales: {estimation.get('territorial_poll_count',0)}\n"
            "No se convierte una encuesta nacional en escaños por inferencia."
        )
    if not snapshot:
        return "PREDICCIÓN: BLOQUEADA\nNo existe snapshot territorial materializado.\nNo se convierte una encuesta nacional en escaños por inferencia."
    projection=snapshot.get("projection",{})
    seats=projection.get("national_seats") or projection.get("party") or {}
    if not isinstance(seats,dict) or not seats:
        return "PREDICCIÓN: BLOQUEADA\nEl snapshot no contiene escaños nacionales verificables."
    rows=sorted(((str(p),int(v)) for p,v in seats.items()),key=lambda x:(-x[1],x[0]))
    return "PROYECCIÓN OBSERVADA\n" + "\n".join(f"{p}: {s}" for p,s in rows)

def _polls_text()->str:
    polls=sorted(_latest_polls(),key=lambda x:str(x.get("publication_date","")),reverse=True)
    if not polls: return "ENCUESTAS\nNo hay observaciones validadas materializadas."
    lines=[f"ENCUESTAS · {len(polls)} observaciones validadas", "Fuente de datos: registros materializados del monitor.", ""]
    for i,poll in enumerate(polls[:5]):
        parties=poll.get("parties") or {}
        if not isinstance(parties,dict): continue
        vals=", ".join(f"{p} {float(v):.1f}%" for p,v in sorted(parties.items(),key=lambda x:(-float(x[1]),str(x[0])))[:8])
        lines += [f"{i+1}. {poll.get('publication_date','?')} · {poll.get('pollster',poll.get('source_id','?'))}", vals]
        if i+1<len(polls):
            prev=polls[i+1].get("parties") or {}
            if isinstance(prev,dict):
                changes=", ".join(f"{p} {_fmt_delta(parties,prev,p)}" for p in sorted(set(parties)|set(prev),key=lambda x:(-float(parties.get(x,0)),str(x)))[:6])
                lines.append("Cambio vs anterior: "+changes)
        lines.append("")
    territory=sum(1 for p in polls if p.get("territorial"))
    lines.append(f"Territoriales explícitas: {territory}/ {len(polls)}")
    if not territory: lines.append("Escaños: BLOQUEADOS hasta disponer de observación territorial verificable.")
    return "\n".join(lines)[:4090]

def _urgencies_text()->str:
    state=_load_json(STATE) or {}
    estimation=_load_json(ESTIMATION) or {}
    obs=_observations()
    issues:list[str]=[]
    if estimation.get("status")=="BLOCKED":
        issues.append("PREDICCIÓN BLOQUEADA: faltan observaciones territoriales explícitas.")
    if not _latest_polls():
        issues.append("No hay sondeos validados materializados.")
    sources=state.get("sources") or state.get("source_health") or []
    if isinstance(sources,dict):
        sources=[{"id":k,**(v if isinstance(v,dict) else {"status":v})} for k,v in sources.items()]
    if isinstance(sources,list):
        failed=[]
        for s in sources:
            if not isinstance(s,dict): continue
            status=str(s.get("status",s.get("health",""))).upper()
            if status in {"DOWN","FAILED","ERROR","DEGRADED","UNHEALTHY"}:
                failed.append(str(s.get("id",s.get("source_id",s.get("name","?")))))
        if failed:
            issues.append("Fuentes con incidencia: "+", ".join(failed[:8]))
    if not issues:
        issues.append("Sin bloqueos críticos materializados.")
    return ("URGENCIAS · ESTADO OPERATIVO\n\n"
            + "\n".join(f"• {x}" for x in issues)
            + "\n\nNo recomienda decisiones políticas: identifica hechos, bloqueos y evidencia pendiente.")

def _sources_text()->str:
    state=_load_json(STATE) or {}
    sources=state.get("sources") or state.get("source_health") or []
    if isinstance(sources,dict):
        sources=[{"id":k,**(v if isinstance(v,dict) else {"status":v})} for k,v in sources.items()]
    if not isinstance(sources,list) or not sources:
        return "FUENTES\nNo hay estado de fuentes materializado."
    lines=["FUENTES · SALUD MATERIALIZADA",""]
    for s in sources[:30]:
        if not isinstance(s,dict): continue
        sid=s.get("id",s.get("source_id",s.get("name","?")))
        status=s.get("status",s.get("health","UNKNOWN"))
        err=s.get("error") or s.get("last_error")
        line=f"{sid}: {status}"
        if err: line += f" · {str(err)[:140]}"
        lines.append(line)
    return "\n".join(lines)[:4090]

def _status_text()->str:
    obs=_observations()
    state=_load_json(STATE) or {}
    polls=_latest_polls()
    estimation=_load_json(ESTIMATION) or {}
    sources=state.get("sources")
    source_count=len(sources) if isinstance(sources,list) else "n/d"
    latest=max((str(p.get("publication_date","")) for p in polls),default="n/d")
    return (
        "ESTADO COALICIÓN\n"
        f"Monitor: {state.get('status','UNKNOWN')}\n"
        f"Observaciones validadas: {len(polls)}\n"
        f"Última publicación: {latest}\n"
        f"Fuentes registradas: {source_count}\n"
        f"Territoriales 52 circunscripciones: {obs.get('territorial_poll_count',0)}\n"
        f"Predicción: {estimation.get('status','SIN_EJECUCIÓN')}\n"
        "Metodología: NOT_PROMOTED hasta OOS + calibración reales\n"
        "Política: fail-closed · sin datos sintéticos · sin inferencia nacional→territorial"
    )

def _radar_text()->str:
    estimation=_load_json(ESTIMATION) or {}
    radar=estimation.get("radar") or {}
    alerts=radar.get("alerts") or []
    if not radar:
        return "RADAR\nSin radar materializado."
    lines=[f"RADAR · {radar.get('as_of','n/d')} · {radar.get('status','UNKNOWN')}",f"Alertas: {len(alerts)}",""]
    for a in alerts[:8]:
        lines.append(f"[{a.get('priority','P4')}] {a.get('title','')} · {a.get('facts',{})}")
    if estimation.get("status")=="BLOCKED":
        lines += ["","BLOQUEO PREDICTIVO","Faltan observaciones territoriales explícitas; no se generan escaños."]
    return "\n".join(lines)[:4090]

def render_command(command:str)->str:
    command=command.split("@",1)[0].strip().lower()
    if command in {"/start","/ayuda","/help"}:
        return ("COALICIÓN · vigilancia electoral neutral\n\n"
                "/urgencias — bloqueos y problemas que requieren atención\n"
                "/prediccion — estado de la proyección y bloqueo real\n"
                "/encuestas — observaciones y cambios entre sondeos\n"
                "/fuentes — salud y errores de fuentes\n"
                "/estado — estado operativo y cobertura\n"
                "/radar — alertas y bloqueos actuales\n"
                "/ayuda — ayuda")
    if command=="/urgencias": return _urgencies_text()
    if command=="/prediccion": return _prediction_text()
    if command=="/encuestas": return _polls_text()
    if command=="/fuentes": return _sources_text()
    if command=="/estado": return _status_text()
    if command=="/radar": return _radar_text()
    return "Comando no reconocido. Usa /ayuda."

def poll_once(offset:int|None=None)->int|None:
    params:dict[str,Any]={"timeout":0,"allowed_updates":["message"]}
    if offset is not None: params["offset"]=offset
    payload=_api("getUpdates",params=params)
    next_offset=offset
    for update in payload.get("result") or []:
        if not isinstance(update,dict): continue
        update_id=update.get("update_id")
        if isinstance(update_id,int): next_offset=update_id+1
        message=update.get("message") or {}
        chat_id=(message.get("chat") or {}).get("id")
        text=str(message.get("text") or "").strip()
        if chat_id is not None and text.startswith("/"):
            send_message(int(chat_id),render_command(text.split()[0]))
    return next_offset

def run_polling(*,poll_timeout:int=25,sleep_seconds:float=1.0)->None:
    _token()
    offset=None
    while True:
        params:dict[str,Any]={"timeout":poll_timeout,"allowed_updates":["message"]}
        if offset is not None: params["offset"]=offset
        payload=_api("getUpdates",params=params)
        for update in payload.get("result") or []:
            if not isinstance(update,dict): continue
            update_id=update.get("update_id")
            if isinstance(update_id,int): offset=update_id+1
            message=update.get("message") or {}
            chat_id=(message.get("chat") or {}).get("id")
            text=str(message.get("text") or "").strip()
            if chat_id is not None and text.startswith("/"):
                send_message(int(chat_id),render_command(text.split()[0]))
        if sleep_seconds: time.sleep(sleep_seconds)

if __name__=="__main__": run_polling()
