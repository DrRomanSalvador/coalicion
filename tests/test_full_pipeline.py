from src.pipeline.full_election import run_full_election

def test_full_pipeline_blocks_without_explicit_territorial_input():
    result = run_full_election(poll={"id":"demo"}, territorial_votes=None, seats=None, blank=None)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "BLOCKED_NO_EXPLICIT_TERRITORIAL_INPUT"
    assert result["policy"]["national_to_territorial_inference"] is False

def test_full_pipeline_is_reproducible_on_explicit_input():
    votes = {f"c{i}":{"A":6000+i,"B":4000-i} for i in range(1,53)}
    seats = {f"c{i}":6 for i in range(1,53)}
    seats["c1"] = 44
    blank = {f"c{i}":100 for i in range(1,53)}
    a = run_full_election(poll={"id":"demo"}, territorial_votes=votes, seats=seats, blank=blank)
    b = run_full_election(poll={"id":"demo"}, territorial_votes=votes, seats=seats, blank=blank)
    assert a["status"] == b["status"] == "PASS"
    assert a["output_hash"] == b["output_hash"]
    assert sum(a["national_seats"].values()) == 350
