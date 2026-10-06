# Reproducibilidad

El núcleo electoral es determinista y usa Fraction; no depende de RNG. Las simulaciones estocásticas existentes siguen el contrato PCG64 del repositorio.

Misma entrada + mismo commit + misma configuración producen el mismo resultado y los mismos hashes en el modo determinista.

La imagen Docker fija Python y las dependencias de CI mediante requirements.lock.

Límite actual: la certificación oficial 2023 continúa bloqueada por la ausencia del binario primario fijado por SHA-256. No se presenta como certificada.
