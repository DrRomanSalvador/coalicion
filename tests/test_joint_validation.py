from src.joint_validation import JointScore, dominates

def test_vote_only_improvement_cannot_hide_seat_worsening():
    base = JointScore(1.0, 1.2, 2.0, 2.4)
    candidate = JointScore(0.8, 1.0, 2.1, 2.5)
    assert not dominates(base, candidate)

def test_candidate_must_strictly_improve_something():
    base = JointScore(1.0, 1.2, 2.0, 2.4)
    same = JointScore(1.0, 1.2, 2.0, 2.4)
    assert not dominates(base, same)

def test_dominating_candidate_is_accepted():
    base = JointScore(1.0, 1.2, 2.0, 2.4)
    candidate = JointScore(0.9, 1.1, 1.8, 2.2)
    assert dominates(base, candidate)
