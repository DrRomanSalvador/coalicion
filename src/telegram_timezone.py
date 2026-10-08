"""Centralized Europe/Madrid clock for the Telegram operational layer."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")

def now_madrid() -> datetime:
    return datetime.now(MADRID_TZ)

def today_madrid() -> date:
    return now_madrid().date()
