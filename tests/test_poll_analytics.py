from src.poll_monitor import Poll
from src.poll_analytics import aggregate, by_pollster, detect_anomalies, relevant_movements, time_series


def p(i, date, house, pp, psoe):
    return Poll(i, date, house, house, "https://example.test", {"PP": pp, "PSOE": psoe, "VOX": 10, "SUMAR": 8, "PODEMOS": 5})


def test_poll_analytics():
    rows=[p("a","2026-10-01","A",30,30), p("b","2026-10-02","A",32,29), p("c","2026-10-03","B",31,28)]
    assert round(aggregate(rows)["PP"], 6) == 31
    assert set(by_pollster(rows)) == {"A","B"}
    assert len(time_series(rows)) == 3
    assert relevant_movements(rows, threshold=1)


def test_poll_anomaly_detection():
    rows=[p("a","2026-10-01","A",30,30),p("b","2026-10-02","A",30,30),p("c","2026-10-03","A",30,30),p("d","2026-10-04","A",50,30)]
    assert any(x["poll_id"]=="d" and x["party"]=="PP" for x in detect_anomalies(rows))
