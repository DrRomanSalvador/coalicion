from src.poll_monitor import Poll
from src.poll_validator import validate_poll

def test_validator_accepts_valid_poll():
    p=Poll("p","2026-10-07","Demo","x","https://example.test",
           {"PP":30.0,"PSOE":28.0,"VOX":18.0,"SUMAR":6.0,"PODEMOS":4.0})
    assert validate_poll(p)[0] is True

def test_validator_rejects_invalid_date():
    p=Poll("p","2026-02-30","Demo","x","https://example.test",
           {"PP":30.0,"PSOE":28.0,"VOX":18.0,"SUMAR":6.0,"PODEMOS":4.0})
    assert validate_poll(p)==(False,"INVALID_PUBLICATION_DATE")
