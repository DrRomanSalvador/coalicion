from src.bias_filter import Observation, select_best

def test_no_oos_returns_error():
    data = [Observation("2023","A",30,31,field_end="2023-07-20")]
    try:
        select_best(data)
    except ValueError:
        assert True
    else:
        assert False

def test_filter_is_deterministic():
    data = [
        Observation("2015","A",30,31,field_end="2015-12-18"),
        Observation("2016","A",30,31,field_end="2016-06-20"),
        Observation("2019A","A",30,31,field_end="2019-04-20"),
        Observation("2019B","A",30,31,field_end="2019-11-05"),
    ]
    assert select_best(data).name == select_best(data).name


def test_oos_scores_elections_equally():
    from src.bias_filter import Observation, Candidate, base, _errors
    observations = [
        Observation("2019", "P", 40.0, 42.0, field_end="2019-01-01"),
        Observation("2023", "P", 40.0, 40.0, field_end="2023-01-01"),
        Observation("2023", "P", 40.0, 40.0, field_end="2023-02-01"),
        Observation("2023", "P", 40.0, 40.0, field_end="2023-03-01"),
    ]
    candidate = Candidate("BASE", base)
    base_score, candidate_score = _errors(candidate, observations)
    assert base_score.mae == 1.0
    assert candidate_score.mae == 1.0
