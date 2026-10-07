from src.poll_normalizer import normalize_party_name

def test_party_aliases_are_normalized():
    assert normalize_party_name("Partido Popular")=="PP"
    assert normalize_party_name("EAJ-PNV")=="PNV"
    assert normalize_party_name("Sumar")=="SUMAR"
