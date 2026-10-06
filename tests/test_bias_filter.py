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
