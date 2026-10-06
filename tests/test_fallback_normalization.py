from scripts.acquire_2023_matrix import slug


def test_territorial_aliases_resolve_to_same_slug():
    assert slug("Valencia") == slug("València") == slug("País Valencià") == "valencia-valencia"
    assert slug("Balears, Illes") == slug("Illes Balears") == slug("Baleares") == "balears-illes"
    assert slug("A Coruña") == slug("La Coruña") == "a-coruna"
    assert slug("Araba") == slug("Álava") == "araba-alava"
    assert slug("Bizkaia") == slug("Vizcaya") == "bizkaia"
    assert slug("Gipuzkoa") == slug("Guipúzcoa") == "gipuzkoa"


def test_slug_resolution_does_not_depend_on_accents_or_case():
    assert slug("VALÈNCIA") == "valencia-valencia"
    assert slug("  Illes   Balears ") == "balears-illes"
