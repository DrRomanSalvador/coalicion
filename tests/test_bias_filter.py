from src.data import PollObservation
from src.prediction import select_best

def test_prediction_module_is_canonical():
    data=[PollObservation("2015","2015-01-01","A",30,31,"H","2015-12-18","test"),
          PollObservation("2016","2016-01-01","A",30,31,"H","2016-06-20","test")]
    assert select_best(data).name in {"BASE","BIAS_COMUN","BIAS_PARTIDO_SHRINK"}
