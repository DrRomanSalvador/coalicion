from src.error_registry import ERRORS, is_blocking, validate_code

def test_all_registered_errors_are_known_and_blocking_where_required():
    assert ERRORS
    for code in ERRORS:
        validate_code(code)
    assert is_blocking("PRIMARY_HASH_MISMATCH")
    assert is_blocking("METHODOLOGY_DRIFT")
    assert is_blocking("NONDETERMINISTIC_EXECUTION")
