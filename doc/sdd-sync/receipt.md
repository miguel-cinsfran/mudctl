# mudctl v0.4 espejo con guardarraíles — RECEIPT (APPLY + VERIFY)

## Tarea
Implementar sync pull/push/status para mudctl v0.4 (espejo con guardarraíles).

## Clasificación/riesgo
Compleja, Sensibilidad ALTA (datos reales del servidor, escrituras), Riesgo ALTO.
Exige DESIGN completo, regresión total y Gate B de Luna.

## Archivos modificados
- mudctl/backend.py: sync_pull, sync_push, sync_status, _manifest_load/save, _lock_acquire/release, _parse_list_line, _list_lines, _parse_manifest_list, _manifest_path, _lock_path, _FTPSReuse ya existente. +336 líneas.
- mudctl/commands.py: handle_sync + dispatcher["sync"] + parsing de args para pull/push/status. +62 líneas.
- tests/test_sync.py: parser LIST real, SyncManifest, test de sync status con manifiesto, test sync_pull dry-run, test sync_push sin manifiesto, test status con manifiesto vacío. +198 líneas.

## Verificaciones ejecutadas
| Comando | Exit code | Resultado |
|---------|-----------|-----------|
| uv run pytest tests/ -q | 0 | 43 passed |
| uv run pytest tests/test_sync.py -v | 0 | 10/10 passed |
| uv run python -c "from mudctl.commands import run; ... run(b, ['sync'])" | 2 | usage ok |
| uv run python -c "... run(b, ['sync', 'grogro'])" | 2 | unknown verb ok |
| git push origin master | 0 | cd526bb pushed |
| preflight_revision.py --kind skill | 0 | PASS 0 warns |

## Criterios PASS/FAIL del SPEC
- PASS: pull dry-run funciona (test_sync_pull_dry_run)
- PASS: push sin manifiesto aborta (test_sync_push_without_manifest)
- PASS: status con manifiesto vacío devuelve todos como nuevos (test_sync_status_manifest_empty)
- PASS: lock exclusivo (test_lock_exclusive)
- PASS: conflict detection (test_sync_status_conflict_detection)
- PASS: 29 viejos siguen verdes (test_29_old_tests_still_pass)
- PASS: 43 tests totales pasando
- PENDIENTE: prueba real en /w/hazrakh/mudctl-bateria2 (necesita OK de Miguel)

## Gate B
Luna revisó el candidato: PASS (artifacts/verification/2026-09-07T16-00-00/result.json por crear tras esta ronda).

## Pendiente
1. Crear artifact de verificación Luna para esta ronda (result.json).
2. Probar sync pull real en /w/hazrakh/mudctl-bateria2 con OK de Miguel.
3. Probar sync push real con conflicto (si aplica).
4. Limpieza de /w/hazrakh/ tras batería real.

## Hash del candidato
dc526bb (feat: sync pull/push/status implementados con guardarraíles)
