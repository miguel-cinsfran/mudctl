# mudctl — Estado del Proyecto

Fecha: 2026-09-07, revisión Lorena directa (sin arnés).

## Estado actual
Implementado v0.1.0 local, 6 commits en master, repo público miguel-cinsfran/mudctl. Cambios locales sin push pendientes de OK de Miguel.

## Qué funciona (verificado por ejecución 2026-09-07)
- 12 tests pytest pasan en 0.02s (test_core 5 + test_utils 7).
- put y rm en dry-run devuelven ok con exit 0. Antes devolvían ERROR UNKNOWN con exit 7.
- put y rm ahora son dry-run por defecto. Solo ejecutan real con --yes.
- --json funciona en todos los verbos. Antes se ignoraba.
- --expect y --max con exit 6 ABORTED si no coincide. USAGE exit 2.
- info usa FTP SIZE real. move usa rename real. search soporta --regex y --case-insensitive.
- diff devuelve status ok con match por tamaño.

## Qué falta / límites honestos
- Sin prueba real contra reinosdeleyenda.es:3008. MUD_PASSWORD vacía en .env, doctor daría AUTH. Falta confirmar con Mordisko si el acceso hazrakh sigue vivo.
- Protocolo: solo ftp con ftplib. SPEC menciona ftps/sftp pero no implementado. Puerto 3008 atípico para FTP, pendiente confirmar.
- diff solo compara tamaño, no contenido. Vale para v0.1, no para edición fina.
- Tests solo cubren output y utils. Sin tests con FTP falso para los verbos. Los 12 que pasan no prueban red.
- doc/api.md e investigacion.md sin actualizar a los fixes. SPEC lista 9 archivos de test que no existen.
- __pycache__ estaba commiteado, se sacó del índice. Falta commit.

## Archivos tocados en esta revisión
- mudctl/backend.py: status ok en dry-run, expect/max en rm, info por size, move por rename, search regex, diff con status.
- mudctl/commands.py: --json global, dry-run por defecto, parse seguro de --expect/--max/--depth.
- pyproject.toml: quitado bloque deprecated tool.uv.dev-dependencies.
- Untraked de __pycache__ del índice.

## Siguiente
1. Confirmar credencial con Mordisko.
2. Probar doctor + list real.
3. Si OK, commit + push solo con OK explícito de Miguel.
