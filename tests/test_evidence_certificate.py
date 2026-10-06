from src.evidence_certificate import (
    sector_variance_identity, falsification_metrics, certificate_for_context
)
from src.poll_error import PollObservation


def r(e, d, p, poll, actual, house="H", gov="PP"):
    return PollObservation(e,d,p,poll,actual,house,d,"test",governing_party=gov)


def test_exact_variance_identity():
    out = sector_variance_identity([
        r("2023","2023-07-23","PSOE",30,28,"A"),
        r("2023","2023-07-23","PSOE",32,28,"B"),
    ])
    assert abs(out[0].exact_residual) < 1e-12


def test_falsification_metrics_are_reproducible():
    x = falsification_metrics([
        r("2023","2023-07-23","PSOE",30,28),
        r("2023","2023-07-23","PP",20,22),
    ])
    assert x.n == 2
    assert x.mae == 2


def test_missing_context_is_not_called_identified():
    x = certificate_for_context([
        PollObservation("2023","2023-07-23","PSOE",30,28,"H","2023-07-20","test")
    ])
    assert x.status == "NO_IDENTIFICABLE"
