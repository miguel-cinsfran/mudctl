# mudctl v0.2 — RECEIPT (aplicar y verificar)

Tarea: carpetas recursivas, copia entre inmos, grep de contenido, scaffold propio. Clasificación Compleja, riesgo alto.

Cambios:
- mudctl/backend.py: MUD_HOME con default barra más usuario, guarda de escritura en put, rm, mkdir, move, cp y scaffold. get y put recursivos con creación de carpetas destino. cp remoto de fichero y árbol. grep de contenido con tope de 2 MB y max hits. scaffold que aborta si el destino existe. mkdir parents real. describe con verbos nuevos.
- mudctl/commands.py: --recursive en get y put, verbos nuevos cp, grep y scaffold, --json heredado, parse seguro.
- mudctl/utils.py: load_config incluye home.
- tests/test_v02.py: nuevo, 6 tests con FTP falso en memoria.
- .env.example: MUD_HOME. README con ejemplos de carpetas y copia. doc/sdd-v02 con spec, design y tasks.

Verificaciones ejecutadas:
- uv run pytest -q: 18 passed en 0.04s (12 viejos más 6 nuevos). Exit 0.
- CLI put fuera de casa: ABORTED exit 6 sin tocar red. PASS.
- CLI cp dry-run con --json: emite JSON válido, falla con NETWORK por credencial muerta. PASS en formato, pendiente red real.
- get -r, put -r, cp, scaffold y grep probados contra falso en memoria con bytes iguales. PASS.

Criterio: PASS en falso local. FAIL pendiente solo contra servidor real por AUTH fallido con la clave vieja.

Pendientes:
- Probar doctor, list, get -r y grep reales cuando Mordisko pase clave nueva.
- Confirmar la ruta exacta de tu carpeta personal para MUD_HOME.
- Push solo con OK explícito de Miguel.
