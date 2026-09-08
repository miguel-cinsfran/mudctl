# Decisiones (por qué las cosas son así)

- D1 CLI propio en vez de servidor MCP: sin Node ni servidor que mantener, funciona en terminal y lo usa cualquier arnés con un proceso.
- D2 Dry-run por defecto en escritura: put, rm, cp, scaffold, apply y plan muestran antes de tocar. Solo --yes ejecuta.
- D3 Sin historial de operaciones ni backup automático: decisión de Miguel, no se hace git trucho ni archivo sin parar.
- D4 Guarda MUD_HOME: lectura libre en todo el servidor, escritura solo dentro de la carpeta propia. Vive en el backend, ningún verbo la salta.
- D5 LPC_EXTS con .c y .h: grep y status filtran a esas por defecto, --all cubre el resto. Se amplía con el primer listado real.
- D6 Verificación contra falso local: la credencial vieja da AUTH fallido, todo se prueba en memoria hasta tener clave nueva.
- D7 La skill de operadora va al final: primero el programa sólido, después la skill que lo maneja.
