# mudctl v0.3 — TASKS (pasos verificables)

1. LPC_EXTS y filtro en grep y status. Archivos: mudctl/backend.py. Verificación: test, grep por defecto ignora .txt y con --all lo incluye.
2. status local contra remoto. Archivos: mudctl/backend.py. Verificación: test, detecta igual, distinto, solo-local y solo-remoto.
3. tail de logs. Archivos: mudctl/backend.py. Verificación: test, trae las últimas N líneas exactas.
4. watch con snapshot local. Archivos: mudctl/backend.py. Verificación: test, entre dos corridas detecta el fichero nuevo.
5. apply de parche unificado. Archivos: mudctl/backend.py. Verificación: test, dry-run cuenta hunks y con --yes cambia el contenido esperado; parche roto aborta sin subir.
6. plan en lote. Archivos: mudctl/backend.py. Verificación: test, valida 3 ops en dry-run y las aplica con un --yes; error a mitad frena y reporta.
7. Comandos de los cinco verbos. Archivos: mudctl/commands.py. Verificación: CLI con falso, exits 0, 2 y 6 correctos, --json válido.
8. docs con apuntes LPC. Archivos: docs/indice.md, docs/lpc.md. Verificación: lectura, lo verificado separado de lo pendiente.
9. Cierre: receipt más artefacto. Archivos: doc/sdd-v03/receipt.md, artifacts/verification/<fecha>/result.json. Verificación: pytest completo en verde y JSON válido.
