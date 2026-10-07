from src.poll_monitor import Poll
from src.poll_hasher import poll_hash, poll_identity

def test_hash_and_identity_are_deterministic():
    p=Poll("p","2026-10-07","Demo","x","https://example.test",
           {"PP":30.0,"PSOE":28.0,"VOX":18.0,"SUMAR":6.0,"PODEMOS":4.0})
    assert poll_hash(p)==poll_hash(p)
    assert poll_identity(p)==poll_identity(p)
