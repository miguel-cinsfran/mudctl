# mudctl v0.3 — RECEIPT (aplicar y verificar)

Tarea: sync con hashes, apply de parches, plan en lote, tail y watch. Más docs con apuntes LPC. Sin historial y sin backup por decisión de Miguel. Clasificación Compleja, riesgo alto.

Cambios:
- mudctl/backend.py: constante LPC_EXTS con .c y .h, filtro en grep con --all para el resto. status local contra remoto por sha256. tail de últimas N líneas. watch con snapshot local. apply de parche unificado que aborta si no calza. plan que valida todo en dry-run y aplica con un solo --yes frenando al primer error. describe con los verbos nuevos.
- mudctl/commands.py: despacho de status, tail, watch, apply y plan. grep con --all. Parse seguro en tail.
- tests/test_v03.py: nuevo, 7 tests con falso en memoria.
- docs/indice.md, docs/lpc.md, docs/recetas.md, docs/mapa.md: cuaderno con lo verificado separado de lo pendiente.
- README con ejemplos de los verbos nuevos.

Verificaciones ejecutadas:
- uv run pytest -q: 25 passed en 0.09s (18 viejos más 7 nuevos). Exit 0.
- CLI con falso: status, tail, watch, apply y plan con exits 0 en ok y 2 en uso. PASS.
- status detecta igual, distinto, solo-local y solo-remoto por hash. PASS.
- apply cambia el contenido esperado y el parche roto aborta sin subir. PASS.
- plan aplica 3 pasos con un --yes y frena con ABORTED ante escritura fuera de casa. PASS.

Pendientes:
- Probar contra el servidor real cuando haya clave nueva.
- Confirmar extensiones LPC además de .c y .h con el primer listado real y ampliar LPC_EXTS.
- Confirmar la ruta de tu carpeta para MUD_HOME.
- Push solo con OK explícito de Miguel.
