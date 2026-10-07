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
    assert polls[0].sample_size is None
