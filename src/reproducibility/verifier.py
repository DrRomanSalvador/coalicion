"""Fail-closed reproducibility verifier."""
from __future__ import annotations
from typing import Any
from .hasher import sha256_json

def verify_same_result(*, input_value: Any, output_a: Any, output_b: Any) -> dict[str, Any]:
    a, b = sha256_json(output_a), sha256_json(output_b)
    return {"status":"PASS" if a == b else "BLOCKED","input_sha256":sha256_json(input_value),"output_a_sha256":a,"output_b_sha256":b,"fail_closed":True}
