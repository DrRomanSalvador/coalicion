# Motor de decisión

La interfaz prevista es:

```bash
python cli.py coalition --input data/processed/2023_constituencies.json --parties PSOE SUMAR
python cli.py marginal --input data/processed/2023_constituencies.json
```

La coalición se recalcula por circunscripción y vuelve a ejecutar D'Hondt; nunca suma escaños de partidos por separado.

Los escenarios de participación usan cuantiles históricos configurables. El modelo conserva por separado:
- resultado observado;
- escenario hipotético;
- parámetros del escenario;
- resultado electoral calculado.

El objetivo principal es la predicción territorial. La calculadora de escrutinio en tiempo real será una segunda interfaz sobre el mismo motor.
