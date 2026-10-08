from __future__ import annotations

import os

import pytest

from src.decision import apply_absolute_shift
from src.electoral import official_2026_seats
from src.neutral_coalition import calculate_coalition
from src.product_layer import _product_envelope
from src.telegram_bot import _chat_allowed, _inline_allowed


def test_official_2026_magnitudes_are_exact():
    seats = official_2026_seats()
    assert len(seats) == 52
    assert sum(seats.values()) == 350
    assert seats["Madrid"] == 38
    assert seats["Cádiz"] == 8
    assert seats["Ceuta"] == 1
    assert seats["Melilla"] == 1


def test_absolute_shift_preserves_vote_mass():
    votes = {
        "A": {"A": 500, "B": 300, "C": 200},
        "B": {"A": 50, "B": 30, "C": 20},
    }
    shifted = apply_absolute_shift(votes, "A", 5, "uniform_by_province")
    assert set(shifted) == set(votes)
    for constituency in votes:
        assert sum(shifted[constituency].values()) == sum(votes[constituency].values())
        assert all(v >= 0 for v in shifted[constituency].values())


def test_negative_absolute_shift_preserves_vote_mass():
    votes = {"A": {"A": 500, "B": 300, "C": 200}}
    shifted = apply_absolute_shift(votes, "A", -5, "uniform_by_province")
    assert sum(shifted["A"].values()) == 1000
    assert shifted["A"]["A"] < votes["A"]["A"]


def test_neutral_coalition_rejects_missing_candidates():
    votes = {"X": {"A": 100, "B": 100}}
    with pytest.raises(ValueError):
        calculate_coalition(votes, {"X": 2}, {"X": 200}, ("A", "C"))


def test_product_envelope_does_not_mutate_result():
    result = {"value": 1, "_engine_result": {"ok": True}, "_input_hash": "abc"}
    before = dict(result)
    out = _product_envelope("test", {"x": 1}, result)
    assert result == before
    assert out["technical"]["engine_result"] == {"ok": True}
    assert out["technical"]["input_hash"] == "abc"


def test_telegram_chat_allowlist_is_fail_closed(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    assert _chat_allowed("123") is False
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123,456")
    assert _chat_allowed("123") is True
    assert _chat_allowed("999") is False


def test_telegram_inline_allowlist_is_fail_closed(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    update = {"inline_query": {"from": {"id": 123}}}
    assert _inline_allowed(update) is False
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123")
    assert _inline_allowed(update) is True
