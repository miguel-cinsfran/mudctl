# mudctl v0.2 — TASKS (pasos verificables)

1. Guarda de escritura en backend. Archivos: mudctl/backend.py. Verificación: test de guarda, escritura fuera de casa aborta con ABORTED sin red.
2. get y put recursivos en backend. Archivos: mudctl/backend.py. Verificación: test con falso, árbol de 3 ficheros baja y sube con bytes iguales.
3. cp remoto y scaffold en backend. Archivos: mudctl/backend.py. Verificación: test, cp duplica contenido en el falso, scaffold aborta si destino existe.
4. grep de contenido en backend. Archivos: mudctl/backend.py. Verificación: test, encuentra texto en subcarpeta con ruta y línea.
5. mkdir parents real. Archivos: mudctl/backend.py. Verificación: test, crea /a/b/c de a niveles.
6. Comandos: --recursive en get/put, verbos cp, grep, scaffold. Archivos: mudctl/commands.py. Verificación: CLI con falso, exits 0 en ok, 2 en uso, 6 en abortado, --json emite JSON.
7. Docs y ejemplo de env. Archivos: .env.example, README.md, SPEC.md. Verificación: lectura, MUD_HOME y verbos documentados.
8. Cierre: receipt más artefacto de verificación. Archivos: doc/sdd-v02/receipt.md, artifacts/verification/<fecha>/result.json. Verificación: pytest completo en verde y JSON válido.
