"""Bounded retry helper with fail-closed semantics."""
from __future__ import annotations
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(fetch: Callable[[], T], *, attempts: int = 3, fallback: Callable[[], T] | None = None) -> T:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last: Exception | None = None
    for _ in range(attempts):
        try:
            return fetch()
        except Exception as exc:
            last = exc
    if fallback is not None:
        return fallback()
    raise RuntimeError("BLOCKED_SOURCE_FETCH_AFTER_RETRIES") from last
