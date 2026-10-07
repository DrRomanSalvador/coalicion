from src.data import PollObservation
from src.prediction import evaluate,select

def make(e,d,party,poll,actual,house,gov):
    return PollObservation(e,d,party,poll,actual,house,d,"test",governing_party=gov,government_status="incumbent_government")

def test_context_evaluation_is_temporal():
    rows=[make("2004","2004-03-14","A",40,42,"H1","PP"),make("2008","2008-03-09","A",40,42,"H1","PSOE"),make("2011","2011-11-20","A",40,42,"H1","PSOE")]
    assert evaluate(rows)["BASE"].n_elections==2

def test_no_future_data_is_used_for_first_election():
    rows=[make("2004","2004-03-14","A",40,42,"H1","PP"),make("2008","2008-03-09","A",40,42,"H1","PSOE")]
    assert evaluate(rows)["BASE"].n_elections==1

def test_selection_never_returns_unknown():
    rows=[make("2004","2004-03-14","A",40,42,"H1","PP"),make("2008","2008-03-09","A",40,42,"H1","PSOE")]
    assert select(rows) in {"BASE","HOUSE","PARTY","GOVERNMENT","HOUSE_PARTY","GOVERNMENT_PARTY"}
