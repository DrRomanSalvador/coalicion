from src.prediction_engine import apply_share_swing, historical_share_changes, predict

def test_historical_median_share_change_is_explicit_and_deterministic():
    current={"A":{"X":600,"Y":400}}
    hist=[{"A":{"X":500,"Y":500}},{"A":{"X":550,"Y":450}},{"A":{"X":520,"Y":480}}]
    d=historical_share_changes(hist,current)
    assert d["A"]["X"]==0.08

def test_share_swing_changes_party_composition_not_just_total_votes():
    out=apply_share_swing({"A":{"X":600,"Y":400}},{"A":{"X":0.05,"Y":-0.05}})
    assert out["A"]["X"]==650
    assert out["A"]["Y"]==350
    assert sum(out["A"].values())==1000

def test_predict_preserves_seats_and_uses_exact_allocator():
    r=predict(
        {"A":{"X":600,"Y":400}},
        {"A":2},
        {"A":0},
        {"A":{"X":0.05,"Y":-0.05}},
    )
    assert sum(r["national_seats"].values())==2
