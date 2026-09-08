# mudctl v0.3 — DESIGN (cómo)

Enfoque: cinco verbos nuevos sobre la base v0.2, sin dependencias nuevas. La guarda MUD_HOME se reutiliza tal cual. Todo cambio remoto pasa por dry-run primero.

Archivos:
- mudctl/backend.py: LPC_EXTS, status, apply, plan, tail, watch.
- mudctl/commands.py: despacho y flags de los cinco verbos.
- tests/test_v03.py: falso en memoria extendido con logs y hashes.
- docs/indice.md, docs/lpc.md: apuntes verificados y pendientes.
- .env.example y README: nada nuevo salvo que status y plan usen MUD_HOME igual que el resto.
- doc/sdd-v03/receipt.md y artefacto de verificación al cierre.

Decisiones:
- LPC_EXTS = {".c", ".h"} en backend.py como constante. grep, status y apply filtran a esas por defecto; --all desactiva el filtro. Cuando veamos el listado real se agregan las que falten sin tocar lógica.
- status local contra remoto: baja cada fichero remoto a memoria y compara sha256 contra el local. No trae todo al contexto, solo devuelve tabla de estados. Para árboles grandes acepta --all o una subruta.
- apply: recibe un fichero de parche unificado local y una ruta remota. En dry-run muestra cuántos hunks tocarían y las líneas afectadas. Con --yes baja el remoto, aplica el parche en memoria con una implementación mínima de unified diff, y lo sube. Si el parche no calza, aborta sin subir nada.
- plan: un JSON con lista de operaciones ya soportadas (put, cp, rm, mkdir, move, scaffold, apply). Primero valida todo en dry-run y cuenta. Con --yes ejecuta en orden y frena al primer error, reportando qué quedó hecho y qué no. Un solo --yes para todo el lote.
- tail: baja el fichero y devuelve las últimas N líneas (default 30). Para logs del MUD.
- watch: guarda un snapshot del listado de una ruta en un fichero local (por defecto .mudctl-watch.json en la carpeta de trabajo). Cada corrida compara contra el snapshot y lista nuevos, borrados y cambiados por tamaño. Solo lectura, nunca escribe en el servidor.
- apply y plan escriben solo dentro de MUD_HOME igual que el resto. tail, watch y status leen donde sea.

Riesgos:
- El apply mínimo puede no cubrir parches con offsets raros. Si un hunk no calza exacto, se aborta en vez de adivinar. Eso es intencional.
- status baja ficheros a memoria para hashear. Con --max-bytes se salta ficheros gigantes con aviso.
- El LIST real puede tener otro dialecto. Se usa el mismo _walk_remote de v0.2, que ya degrada de MLSD a LIST.

Orden: backend por verbos (status, tail, watch, apply, plan), comandos, tests, docs.
