# COALICIÓN — sistema integrado de inteligencia electoral

La capa de inteligencia no sustituye a los motores canónicos. Los ensambla bajo un único contrato verificable:

fuentes primarias → ingestión → validación → OOS → calibración → predicción → territorialización → escaños → incertidumbre → marginalidad → contrafactuales → decisión → monitorización → auditoría → reproducibilidad.

## Componentes conectados

- \`config/political_intelligence_sources.json\`: registro de fuentes y precedencia.
- \`src/political_intelligence.py\`: contrato único, grafo de evidencia, estado de componentes y gates.
- \`src/poll_monitor.py\` + \`src/poll_analytics.py\`: vigilancia y análisis descriptivo de encuestas.
- \`src/oos_pipeline.py\`: validación temporal fuera de muestra.
- \`src/probabilistic_calibration.py\` + \`src/uncertainty.py\`: calibración e incertidumbre explícitas.
- \`src/prediction.py\`: capa estadística canónica.
- \`src/electoral.py\`: asignación electoral canónica.
- \`src/marginality.py\`: escaños marginales.
- \`src/coalition.py\`: contrafactuales matemáticos.
- \`src/rapid_decision_center.py\`: snapshot de decisión reproducible.
- \`src/electoral_intelligence.py\`: radar descriptivo.
- \`src/evidence_certificate.py\` + \`src/reproducibility_contract.py\`: evidencia y reproducibilidad.

## Estados

\`REGISTERED → MATERIALIZED → VALIDATED → OOS → CALIBRATED → AUDITED → CERTIFIED\`.

Registrar una URL nunca equivale a materializarla ni a certificarla. El sistema falla cerrado cuando falta evidencia esencial.

## Manifest

\`scripts/build_political_intelligence_manifest.py\` genera \`artifacts/political_intelligence_manifest.json\` con el hash del snapshot y hashes SHA-256 de componentes físicos presentes. CI lo publica como artefacto para evitar certificar estados que no se han ejecutado.

## Neutralidad

El sistema describe hechos, incertidumbre y contrafactuales electorales. No implementa persuasión, microsegmentación política ni recomendación de voto o de pacto. Las coaliciones son simulaciones matemáticas, no probabilidades de negociación.
