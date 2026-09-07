# mudctl v0.2 — DESIGN (cómo)

Enfoque: extender el backend real con recursión sobre ftplib y guardas de escritura, más tres verbos nuevos. Sin dependencias nuevas, solo stdlib. Los tests usan un falso en memoria, no red.

Archivos a tocar:
- mudctl/backend.py: MUD_HOME, guarda de escritura, get/put recursivos, cp remoto, grep contenido, scaffold, mkdir con parents real.
- mudctl/commands.py: flags --recursive en get/put, verbos cp, grep y scaffold, con --json heredado y parse seguro.
- tests/test_v02.py: nuevo, falso en memoria que imita ftplib para probar sin red.
- .env.example y README: documentar MUD_HOME y los verbos nuevos.
- doc/sdd-v02/receipt.md y artifacts: evidencia al cierre.

Decisiones:
- MUD_HOME: variable nueva, default /hazrakh (barra más usuario). Todo destino de escritura debe empezar por ahí. La lectura no se limita. Si el servidor usa otra ruta, se cambia por .env sin tocar código.
- Recursión remota: con MLSD si el servidor lo soporta, si no con LIST parseado simple. El falso local usa MLSD.
- cp remoto: FTP clásico no tiene copia en servidor, se hace RETR más STOR interno sin pasar por disco. Para el usuario es como si fuera directo.
- grep: baja cada fichero a memoria y busca por texto o regex, con límite de tamaño de 2 MB por fichero para no llenar memoria ni contexto. Devuelve ruta más línea.
- scaffold: es un cp que además aborta si el destino ya existe, para no pisar trabajo propio por accidente.
- mkdir --parents: crea nivel por nivel ignorando los que ya existen.
- Seguridad: la guarda vive en el backend, no en el comando. Ningún verbo de escritura llega a red si el destino está fuera de casa. put y rm siguen en dry-run por defecto.
- put -r real exige --yes más --expect con el conteo de ficheros, igual que rm. Así un llm no sube 200 ficheros por error de conteo.

Riesgos:
- El LIST de cada servidor FTP tiene formato distinto. Se intenta MLSD primero y se degrada a LIST simple. Si el real usa otro dialecto, se ajusta al probar con clave nueva.
- Ficheros grandes del MUD en grep: se capan a 2 MB con aviso. No se traen binarios enteros al contexto.
- mover carpetas enteras con move queda fuera: move sigue siendo de fichero, la copia de árboles la hace cp más rm.

Orden: backend primero con guarda y recursión, después comandos, después tests, después docs.
