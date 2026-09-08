# mudctl v0.3 — SPEC (qué)

Objetivo: sync con hashes, aplicar parches, planes en lote, tail de logs y watch de carpetas ajenas. Más carpeta docs con apuntes LPC y extensiones conocidas.

Recorte de Miguel (2026-09-07): fuera historial y fuera backup. No se hace git trucho ni archivo sin parar.

Entradas:
- Repo mudctl v0.2 en master (commit 2f7699a).
- Servidor real inaccesible (AUTH fallido con clave vieja). Todo se verifica contra falso local.
- RdL corre MudOS con mudlib propia pusa. LPC verificado: .c son objetos (cada fichero .c es un objeto), .h son cabeceras para inherit e includes.
- Extensiones dudosas: Miguel recuerda una o dos más pero no cuáles. No invento: grep, status y apply trabajan por defecto con .c y .h, con flag --all para todo, y la lista vive en una constante LPC_EXTS fácil de ampliar cuando veamos el listado real.

Clasificación: Compleja, Riesgo alto (múltiples archivos, aplica cambios remotos). Sensibilidad media (verificación contra falso local).

Criterios de éxito:
- PASS: status compara árbol local contra remoto y dice igual, distinto, solo-local y solo-remoto.
- PASS: apply aplica un parche unificado a un fichero remoto con preview en dry-run y cambio real con --yes.
- PASS: plan valida un plan.json entero en dry-run y lo aplica con un solo --yes.
- PASS: tail trae las últimas N líneas de un log remoto.
- PASS: watch detecta ficheros nuevos en una carpeta ajena entre dos corridas.
- PASS: grep y status filtran a .c y .h por defecto y cubren todo con --all.
- PASS: docs/indice.md y docs/lpc.md existen con lo verificado y lo pendiente marcado.
- PASS: los 18 tests viejos siguen pasando más los nuevos.

Fuera de alcance:
- Historial de operaciones y backup con restore (descartados por Miguel).
- Probar contra el servidor real (bloqueado hasta clave nueva).
- La skill de operadora (va al final, después del programa).
