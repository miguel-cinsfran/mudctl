# mudctl v0.4 espejo con guardarraíles — DESIGN (cómo)

Patrones de guia-design aplicados desde el arranque: transacción durable (el
manifiesto solo avanza al completar), Regla 0 (ante duda no se avanza nada),
locks con protocolo único, inicialización explícita, errores con formato
contractual (exits 0/2/3/4/5/6 ya existentes), regresión sobre lo verificado
(verbos viejos intactos + batería completa).

## Verbos nuevos (explícitos, como el resto)

- `sync pull <remoto> <local> [--parallel N] [--prune] [--dry-run] [--yes] [--expect N]`
- `sync push <local> <remoto> [--dry-run] [--yes] [--expect N]`
- `sync status <local> <remoto>` (rápido: manifiesto contra LIST, sin RETR)

## Manifiesto (.mudctl-sync.json en la raíz del espejo)

{"remote": "/w/hazrakh", "files": {"a.c": {"size": 400, "mtime": "May 27  2025"},
"updated": "<iso>", "last_run": {"verb": "pull", "counts": {...}}}.
Sin contenido de ficheros (privacidad del estado: metadatos, no texto).
Transacción durable: se escribe a fichero temporal y se renombra solo si todo
el verbo terminó OK. Muerte del proceso a mitad = manifiesto viejo intacto.

## Detección de cambios (rápida, sin RETR)

Parser de LIST unix (regex sobre líneas reales vsFTPd: permisos, tamaño, fecha
"May 27 2025" o "Sep 08 02:23", symlinks con "->"). Un LIST por carpeta = una
conexión de datos. Cambio = (size, mtime) distinto al manifiesto.
Límite honesto: si alguien reescribe un fichero conservando tamaño y fecha
exacta, no se detecta. Se documenta, no se promete.

## Pull

1. Lock (fichero .mudctl-sync.lock con PID; ocupado → ABORTED exit 6).
2. LIST recursivo (con el walk actual) → compara contra manifiesto.
3. Dry-run: lista qué bajaría con conteo (para --expect).
4. Descarga solo lo nuevo/cambiado, en paralelo (ThreadPoolExecutor, N=4 por
   defecto, tope 8; cada worker con su propia conexión FTPS, ftplib no se
   comparte entre hilos).
5. Verificación por fichero: SIZE remoto tras bajar == bytes escritos.
6. Sin --prune: lo borrado en remoto solo se reporta como gone. Con --prune:
   lista explícita + --yes para borrar local.
7. Avanza manifiesto solo al final OK.

## Push

1. Lock igual. Bloqueo si no hay manifiesto ("hacé pull primero", exit 2).
2. Compara local contra manifiesto (cambiados local) y LIST contra manifiesto
   (cambiados remoto). Intersección no vacía = conflicto → ABORTED exit 6 con
   la lista, sin tocar nada.
3. Dry-run + --expect, luego sube solo lo cambiado local (put existente).
4. Re-lee LIST de lo subido y avanza manifiesto.

## Inicialización explícita

pull sin manifiesto = inicialización (lo dice en la salida). push/status sin
manifiesto = error claro, no corrupción silenciosa.

## Archivos a tocar (orden)

1. mudctl/backend.py: parser LIST, manifiesto, sync_pull/push/status, pool.
2. mudctl/commands.py: handle_sync + salidas texto/JSON + exits.
3. tests/test_sync.py: parser con líneas reales, manifiesto, conflictos,
   lock, dry-run (FakeFTP); regresión: 29 viejos verdes.
4. README.md: verbos sync. Skill mudctl-operadora: receta 8 reescrita sobre
   sync (el grep queda como fallback acotado). doc/sdd-sync/receipt.md.
5. Charter para Gate B: los criterios del spec (congelado antes de R1).

## Riesgos y controles

- Hilos + FTPS: cada worker conecta aparte; si el servidor limita conexiones,
  bajar N (flag --parallel, documentado).
- Corte a mitad de pull: manifiesto viejo intacto (renombre atómico); la
  próxima corrida retoma lo que falta.
- Ficheros grandes: tope 2MB por fichero como en grep (se reportan, no se
  bajan en silencio).
- Regresión: ningún verbo viejo cambia de firma ni de comportamiento.
