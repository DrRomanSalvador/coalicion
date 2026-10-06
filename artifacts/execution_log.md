# Autonomous execution log — 2026-10-06

## 20:03 — Baseline
- Commit inicial: 49334640c99fc98b4aa466b75c9b784a001ad961
- Inventario: 73 archivos / 10 directorios.
- CI Colmena run 37523506246: FAIL en `src.colmena_resume` por `UNKNOWN_ERROR_CODE:CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT`.
- Fuente primaria binaria declarada en el contrato: ausente del repositorio.

## 20:42 — Corrección
- Se registró `CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT` en el registro canónico.
- Se añadió regresión para impedir que el estado y el registro vuelvan a divergir.

## 20:43 — Validación CI
- Reanudación pasó.
- Contrato reproducible falló correctamente por `PRIMARY_BINARY_NOT_REPOSITORY_PINNED`.
- Histórico: la fuente oficial XLSX pudo descargarse en CI; la validación histórica ejecutada siguió usando réplica secundaria y mostró discrepancia máxima de votos válidos de 1722.0; esto queda como evidencia no certificante.

## 20:45 — Endurecimiento
- Se añadió oráculo electoral independiente y pruebas diferenciales.
- Monte Carlo alineado con PCG64.
- Escenarios preservan Ceuta/Melilla.
- CI modificado para ejecutar tests independientes aunque falle el contrato y para no hacer push automático a main.

## 21:20 — Decision Engine MVP
- CLI añadido: audit / coalition / scenario / verify.
- Motor determinista de coaliciones añadido: fusiona votos por circunscripción y recalcula D'Hondt.
- Motor de shocks +X añadido con territorialización obligatoria.
- Escenarios ambiguos quedan bloqueados.
- Dockerfile, lock de dependencias y documentación de reproducibilidad añadidos.
- No se generaron casos reales PSOE+SUMAR/PP+VOX porque la matriz oficial candidatura×circunscripción todavía no está materializada; inventarla violaría el contrato.

## 21:35 — Validación
- Suite contractual: PASS (incluye comportamiento fail-closed).
- Gate de reproducibilidad: FAIL intencionado por ausencia del binario primario contractual.
- No se fabricaron resultados PSOE+SUMAR ni PP+VOX porque falta la matriz oficial candidatura×circunscripción.

## 21:55 — OPERATIONAL_BETA
- Producto desbloqueado para uso analítico sobre réplica secundaria.
- La habilitación beta exige manifest SECONDARY_REPLICA + validation PASS + 0 arithmetic_bad_cells.
- Certificación estricta sigue independiente y bloqueada por evidencia primaria pendiente.
- No se han fabricado resultados de PSOE+SUMAR/PP+VOX: falta confirmar/montar una matriz candidatura×circunscripción utilizable.
- 2026-10-06T22:25:36.584302+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=1/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:25:46.849468+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=2/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:26:07.124501+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=3/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:26:37.378405+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=4/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:27:07.662170+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=5/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:27:07.662257+00:00 — ACQUIRE interior: ERROR URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:27:17.639630+00:00 — FETCH https://www.ine.es/pob_xls/pobmun.zip: OK intento=1 sha256=b4251c99ecb1319ddc8e49da12d00e3b0a2343ca4c8ac43ff3382532a221ffb4
- 2026-10-06T22:27:17.647720+00:00 — ACQUIRE ine_pobmun: OK sha256=b4251c99ecb1319ddc8e49da12d00e3b0a2343ca4c8ac43ff3382532a221ffb4
- 2026-10-06T22:27:19.380417+00:00 — FETCH https://www.cis.es/es/estudios/catalogo?catalogo=estudio: OK intento=1 sha256=0763e502ba783009fce3bac1c2add6a93ec2b7e9a06eec4bf4455cda8c43cccf
- 2026-10-06T22:27:19.381226+00:00 — ACQUIRE cis_catalog: OK sha256=0763e502ba783009fce3bac1c2add6a93ec2b7e9a06eec4bf4455cda8c43cccf
- 2026-10-06T22:27:29.746202+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=1/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:27:40.019462+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=2/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:28:00.311434+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=3/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:28:30.584564+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=4/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:29:00.843995+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=5/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:29:00.844084+00:00 — ACQUIRE interior: ERROR URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:29:00.853439+00:00 — ACQUIRE ine_pobmun: OK sha256=b4251c99ecb1319ddc8e49da12d00e3b0a2343ca4c8ac43ff3382532a221ffb4
- 2026-10-06T22:29:00.854427+00:00 — ACQUIRE cis_catalog: OK sha256=0763e502ba783009fce3bac1c2add6a93ec2b7e9a06eec4bf4455cda8c43cccf
- 2026-10-06T22:29:21.212533+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=1/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:29:31.454528+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=2/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:29:51.702290+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=3/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:30:21.943885+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=4/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:30:52.198858+00:00 — FETCH https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx: ERROR intento=5/5 URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:30:52.198961+00:00 — ACQUIRE interior: ERROR URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
- 2026-10-06T22:30:52.208208+00:00 — ACQUIRE ine_pobmun: OK sha256=b4251c99ecb1319ddc8e49da12d00e3b0a2343ca4c8ac43ff3382532a221ffb4
- 2026-10-06T22:30:52.209213+00:00 — ACQUIRE cis_catalog: OK sha256=0763e502ba783009fce3bac1c2add6a93ec2b7e9a06eec4bf4455cda8c43cccf
