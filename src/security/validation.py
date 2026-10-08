"""Fail-closed input validation for public product surfaces."""
from __future__ import annotations
import re

def validate_command(text: str, *, max_length: int = 512) -> str:
    if not isinstance(text, str):
        raise ValueError("BLOCKED_INVALID_INPUT")
    value=text.strip()
    if not value or len(value)>max_length:
        raise ValueError("BLOCKED_INVALID_INPUT")
    if any(ord(ch)<32 and ch not in "\n\t" for ch in value):
        raise ValueError("BLOCKED_INVALID_INPUT")
    return value

def validate_chat_id(chat_id: object) -> int:
    try: value=int(chat_id)
    except (TypeError,ValueError) as exc: raise ValueError("BLOCKED_INVALID_CHAT_ID") from exc
    if value==0 or abs(value)>10**18:
        raise ValueError("BLOCKED_INVALID_CHAT_ID")
    return value
