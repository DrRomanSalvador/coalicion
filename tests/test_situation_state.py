from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.situation_state import SituationStateBlocked, build_situation_state


def test_state_is_fail_closed_and_neutral():
    state = build_situation_state(
        as_of=datetime(2026, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    )
    assert state["policy"]["fail_closed"] is True
    assert state["policy"]["descriptive_only"] is True
    assert state["policy"]["no_persuasion"] is True
    assert state["policy"]["no_national_to_territorial_inference"] is True


def test_state_surfaces_real_territorial_gap():
    state = build_situation_state(
        as_of=datetime(2026, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    )
    assert state["counts"]["territorial_polls"] == 0
    assert state["radar"] == "UNCERTAINTY"
    assert state["headline"]["uncertainties"]


def test_state_is_reproducible_for_same_inputs_and_time():
    when = datetime(2026, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    a = build_situation_state(as_of=when)
    b = build_situation_state(as_of=when)
    assert a["state_hash"] == b["state_hash"]


def test_questions_are_bounded_and_concrete():
    state = build_situation_state(
        as_of=datetime(2026, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    )
    assert 1 <= len(state["headline"]["questions"]) <= 3
    assert all(q["question"].endswith("?") for q in state["headline"]["questions"])


def test_blocking_exception_is_public_api():
    assert issubclass(SituationStateBlocked, RuntimeError)
