import pytest
from src.security.validation import validate_chat_id, validate_command

def test_input_validation_fail_closed():
    assert validate_command(" /situacion ")=="/situacion"
    assert validate_chat_id(123)==123
    with pytest.raises(ValueError): validate_command("")
    with pytest.raises(ValueError): validate_chat_id("bad")
