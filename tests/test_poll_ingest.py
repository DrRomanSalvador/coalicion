from src.poll_ingest import parse_json, parse_csv, poll_hash
SOURCE={"id":"fixture","url":"https://example.test/polls.json"}
def test_json_poll_is_validated_and_normalized():
    body=b'{"polls":[{"id":"p1","publication_date":"2026-10-06","pollster":"Demo","parties":{"PSOE":"31,2","Sumar":8.1},"sample_size":1000}]}'
    polls=parse_json(body,SOURCE)
    assert polls[0].parties=={"PSOE":31.2,"SUMAR":8.1}
    assert poll_hash(polls[0])
def test_csv_poll_is_supported():
    body=b"id,publication_date,pollster,PSOE,SUMAR\np1,2026-10-06,Demo,30.0,8.0\n"
    assert parse_csv(body,SOURCE)[0].parties=={"PSOE":30.0,"SUMAR":8.0}

def test_datoelectoral_html_parser_reads_complete_poll():
    html = """<h3>Barómetro de prueba 2026</h3>
    <p>Demo · publicado el 6 de octubre de 2026 · ámbito: España</p>
    <h4>Estimación de voto publicada por el sondeo</h4>
    <p>PSOE 31,0 %</p><p>PP 25,5 %</p><p>SUMAR 5,7 %</p>
    <p>Cuestionario íntegro y no-respuesta por pregunta</p>"""
    from src.poll_ingest import parse_datoelectoral_html
    polls=parse_datoelectoral_html(html.encode(),{"id":"dato","url":"https://example.test"})
    assert polls[0].parties["PSOE"]==31.0
    assert polls[0].parties["PP"]==25.5
    assert polls[0].parties["SUMAR"]==5.7
    assert "NO-RESPUESTA" not in polls[0].parties
    assert polls[0].sample_size is None


def test_rss_entries_are_metadata_only():
    from src.poll_ingest import parse_rss
    rss = b"""<?xml version="1.0"?><rss><channel>
    <item><title>Electopanel 4 octubre</title><link>https://example.test/p1</link>
    <pubDate>Sun, 04 Oct 2026 08:00:00 +0000</pubDate><guid>p1</guid></item>
    </channel></rss>"""
    polls=parse_rss(rss,{"id":"electomania","url":"https://example.test/feed","pollster_default":"Electomania"})
    assert len(polls)==1
    assert polls[0].parties=={}


def test_poll_report_never_turns_national_sum_into_seat_projection():
    from scripts.build_poll_report import build
    payload=build([{"id":"p1","parties":{"PSOE":31.0,"SUMAR":5.7}}],[["SUMAR","PSOE"]])
    report=payload["reports"][0]
    assert report["national_vote_share_scenarios"][0]["combined_national_vote_share"]==36.7
    assert report["national_vote_share_scenarios"][0]["seat_projection"]=="BLOCKED_NO_TERRITORIAL_INPUT"
    assert report["seat_scenarios"]=="BLOCKED_NO_VALID_TERRITORIAL_INPUT"
