# mudctl v0.4 espejo con guardarraíles — SPEC (qué)

Objetivo: bajar el home (/w/hazrakh) a espejo local, buscar con rg en local y
devolver cambios, sin desfases silenciosos ni borrados sorpresa. El grep remoto
(3m55s para 6 ficheros) y el descenso recursivo (más de 200s sin bajar) medidos
el 2026-09-07 lo hacen inviable para trabajo iterativo.

Fuente: pedido de Miguel 2026-09-07 ("forma inteligente de descargar carpetas y
buscar dentro, con guardarraíles"). Recorte vigente: fuera historial y fuera
backup (decisión previa, no se re-litiga).

Entradas:
- Repo mudctl en master cd34bd9, 29 tests verdes, FTPS con reuso de sesión.
- Servidor real accesible (doctor verde), home /w/hazrakh, MUD_HOME en .env.
- Medición real: ~40s por fichero en RETR; LIST por carpeta rápido (una conexión).
- vsFTPd sin MLSD (500 Unknown command); NLST devuelve rutas completas.
- Formato LIST unix con permisos, tamaño y fecha (líneas reales capturadas).

Clasificación: Compleja (backend, commands, tests, skill, docs), Sensibilidad
ALTA (datos reales del servidor, escrituras), Riesgo ALTO. Exige DESIGN
completo, regresión total y Gate B de Luna tras APPLY.

Criterios de éxito (observables):
- PASS: pull inicial del home escribe manifiesto y trae N ficheros; segunda
  corrida sin cambios descarga 0 y lo dice.
- PASS: cambio remoto de 1 fichero → pull trae solo ese (lo demás intacto).
- PASS: fichero cambiado en ambos lados → push aborta exit 6 listándolo, sin
  tocar nada en ningún lado.
- PASS: sin manifiesto, push y status se niegan con mensaje claro (pull primero).
- PASS: dos corridas a la vez → la segunda falla sin duplicar ni corromper.
- PASS: pull con --prune lista borrados remotos y solo borra local con --yes.
  Sin --prune no borra nada.
- PASS: dry-run + --expect funcionan en pull y push como en el resto.
- PASS: los 29 tests viejos siguen verdes más los nuevos.
- PASS: prueba real en /w/hazrakh/mudctl-bateria2 con limpieza total.
- PASS: Gate B Luna LISTO sobre el candidato.

Fuera de alcance:
- Historial y backup (recorte vigente).
- Cambiar el comportamiento de los verbos viejos (solo se agregan verbos sync).
- SSH, lftp o cualquier herramienta externa (todo dentro de mudctl).
- Búsqueda de contenido en servidor (el protocolo no la tiene; veredicto web).

Pendientes / supuestos explícitos:
- SUPUESTO: fecha del LIST alcanza para detectar cambios (tamaño+fecha;
  hash solo al descargar). Límite honesto documentado, no promesa.
- PENDIENTE: zona horaria del servidor (se guarda fecha cruda + parseada).
- DECISIÓN REQUERIDA de Miguel: OK al contrato para implementar.
