from src.temporal_state import TemporalState
def test_update_reduces_uncertainty():
    s=TemporalState({"A":50.0,"B":50.0}); before=s.uncertainty()["A"]
    s.update("2026-10-06",{"A":55.0,"B":45.0},{"A":4.0,"B":4.0})
    assert s.uncertainty()["A"]<before
