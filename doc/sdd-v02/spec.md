# mudctl v0.2 — SPEC (qué)

Objetivo: subir y bajar carpetas enteras, copiar código ajeno a carpeta propia, buscar en otras carpetas por nombre y contenido, y crear piezas propias desde ejemplos sin pisar nada.

Decisiones de Miguel (2026-09-07):
- Alcance: todo v0.2 (recursivo + copia remota + grep contenido + scaffold).
- Seguridad: lectura libre en todo el servidor, escritura solo dentro de la carpeta propia.
- Verificación: contra FTP falso local, sin tocar el servidor real hasta tener clave nueva.

Entradas:
- Repo mudctl v0.1.0 con fixes Lorena (commit c9a1683).
- Credencial real conocida pero con AUTH fallido, no se usa.
- Sin tarjeta kanban, trabajo directo de Lorena a pedido de Miguel.

Clasificación: Compleja, Riesgo alto (múltiples archivos + guardas de seguridad). Sensibilidad media (sin datos reales en esta ronda, todo contra falso local).

Criterios de éxito observables:
- PASS: get -r baja un árbol completo del falso local y los bytes coinciden.
- PASS: put -r sube un árbol con dry-run que lista todo sin escribir, y con --yes escribe todo.
- PASS: cp copia un archivo remoto a mi carpeta sin bajarlo a disco, con dry-run seguro.
- PASS: grep encuentra un texto dentro de ficheros remotos en subcarpetas.
- PASS: scaffold copia un ejemplo ajeno a un destino nuevo mío, y aborta si el destino ya existe.
- PASS: put, rm, move, cp, mkdir y scaffold con destino fuera de mi carpeta abortan con exit 6 sin tocar nada.
- PASS: los 12 tests viejos siguen pasando más los nuevos.

Fuera de alcance:
- Probar contra el servidor real (bloqueado hasta clave nueva).
- FTPS/SFTP, compilación de LPC, reload del MUD.
- Cambiar el formato de salida ya estable.

Pendientes:
- Confirmar con Mordisko la ruta exacta de tu carpeta personal en el servidor (se asume /hazrakh y se configura por MUD_HOME).
- Probar doctor y list real cuando haya clave nueva.
