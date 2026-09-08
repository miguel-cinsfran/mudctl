# Recetas de trabajo con mudctl — pendiente del servidor real

Se llena cuando haya acceso real. Cada receta con su secuencia de verbos y su verificación.

Recetas previstas:
- Explorar una carpeta ajena: list más grep más tail.
- Copiar un ejemplo y hacerlo propio: cp o scaffold más status.
- Subir un cambio chico: apply con dry-run más status.
- Subir un lote: plan con dry-run más status.
- Vigilar novedades: watch en cada sesión.
- Búsqueda rápida (hallazgo 2026-09-07): el grep remoto sale a ~40s/fichero y el árbol no baja en 200s. FTP no sabe buscar contenido en servidor (consenso web + Reddit r/MUD sin tooling mejor). Opciones: espejo local chico con watch (receta 8 de la skill), lftp mirror --parallel con FTPS (paraleliza conexiones; no instalado, vive en WSL Ubuntu con apt), o pedirle a Satyr búsqueda del lado del servidor. lftp FTPS: set ftp:ssl-force true + ftp:ssl-protect-data true.
