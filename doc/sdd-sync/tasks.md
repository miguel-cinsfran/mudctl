# mudctl v0.4 espejo con guardarraíles — TASKS (pasos verificables)

1. Parser LIST: tests/test_sync.py con líneas vsFTPd reales (fichero, dir,
   symlink, fecha con año y sin año). Verifica: pytest tests/test_sync.py -q.
2. Manifiesto: escribir/leer/avance-atómico en backend. Verifica: test de
   corte simulado deja manifiesto viejo intacto.
3. sync status contra FakeFTP: detecta nuevo/cambiado/borrado sin RETR.
   Verifica: test con conteos exactos.
4. sync pull dry-run + --expect contra FakeFTP. Verifica: no escribe nada.
5. sync pull real + verificación por SIZE + prune con y sin --yes.
   Verifica: tests de cada rama.
6. sync push con conflicto (ambos lados) → ABORTED exit 6 sin tocar nada.
   Verifica: test que lo prueba.
7. Lock concurrente: segunda corrida falla. Verifica: test.
8. Bloqueo sin manifiesto en push/status. Verifica: test.
9. Paralelo: pull con --parallel 4 contra FakeFTP trae todo. Verifica: test.
10. Regresión: pytest tests/ completo en verde (29 viejos + nuevos).
11. CLI real: describe muestra sync; doctor verde.
12. Prueba real en /w/hazrakh/mudctl-bateria2: pull, cambio, push, status,
    limpieza total verificada con list. Solo con OK de Miguel.
13. Docs: README + receta 8 de la skill reescrita + receipt.md + artefacto
    verification/result.json. Verifica: preflight skill PASS 0 warns.
14. Gate B: Luna sobre candidato + evidencia, charter = criterios del spec.
