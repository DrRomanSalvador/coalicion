from src.data import PollObservation
from src.prediction import summarize,by_election,leave_one_election_out,change_vs_previous_election

def row(e,d,p,poll,actual,field,house="H"):
    return PollObservation(e,d,p,poll,actual,house,field,"test")

def test_summary_exact():
    s=summarize([row("2004","2004-03-14","A",40,42,"2004-03-01"),row("2004","2004-03-14","A",44,42,"2004-03-10")])
    assert s.n==2 and s.mean_error==0 and s.mae==2 and s.minimum==-2 and s.maximum==2 and s.p95_abs==2

def test_group_by_election():
    rows=[row("2004","2004-03-14","A",40,42,"2004-03-01"),row("2008","2008-03-09","A",40,39,"2008-03-01")]
    assert set(by_election(rows))=={"2004","2008"}

def test_leave_one_election_out_is_temporal():
    rows=[row("2004","2004-03-14","A",40,42,"2004-03-01"),row("2008","2008-03-09","A",40,39,"2008-03-01"),row("2011","2011-11-20","A",40,41,"2011-11-01")]
    out=leave_one_election_out(rows)
    assert "2004" not in out and "2008" in out and "2011" in out

def test_direction_and_magnitude():
    x=row("2004","2004-03-14","A",45,42,"2004-03-01")
    assert x.error_direction=="SOBREESTIMACION" and x.change_magnitude==3

def test_government_dimensions():
    rows=[PollObservation("2004","2004-03-14","A",45,42,"H","2004-03-01","S","1","PP","incumbent_government"),
          PollObservation("2008","2008-03-09","A",40,42,"H","2008-03-01","S","2","PSOE","incumbent_government")]
    from src.prediction import by_government,by_government_status
    assert set(by_government(rows))=={"PP","PSOE"} and set(by_government_status(rows))=={"incumbent_government"}

def test_change_vs_previous_election():
    rows=[row("2004","2004-03-14","A",40,42,"2004-03-01"),row("2008","2008-03-09","A",45,44,"2008-03-01")]
    out=change_vs_previous_election(rows)
    assert len(out)==1 and out[0].actual_change==2 and out[0].poll_change==3 and out[0].change_error==1
