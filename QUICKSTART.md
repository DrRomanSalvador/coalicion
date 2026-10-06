# COALICIÓN Decision Engine

COALICIÓN ya expone un núcleo determinista para comparar candidaturas separadas frente a una coalición y para ejecutar shocks territoriales explícitos.

Entrada mínima: JSON con las claves votes, seats, valid_votes y opcionalmente special y blank.

Coalición:
python coalicion.py coalition PARTIDO_A PARTIDO_B --input scenario.json

Escenario +X puntos:
python coalicion.py scenario --party PARTIDO_A --shift 2 --distribution uniform_by_province --input scenario.json

Sin distribución territorial explícita, el motor devuelve AMBIGUOUS_SCENARIO y no certifica el resultado.

Importante: esto es un simulador determinista, no un predictor. La certificación oficial 2023 sigue bloqueada hasta completar la evidencia primaria contractual.
