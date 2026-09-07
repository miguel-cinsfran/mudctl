# mudctl — CLI FTP para Reinos de Leyenda

## Estado

**Fase: PROPOSE v1 — tarjeta kanban creada, diseño pendiente de Luna.**
Ver `doc/estado.md` para el detalle completo: qué funciona, qué falta, problemas conocidos y próximos pasos.

## Decisión ya tomada (no re-litigar sin motivo)

- **Forma: CLI propio en Python (uv)**, no MCP server.
  Razón: Hermes ya tiene `terminal`, `code_execution`, `file`, `browser`. Un MCP server para FTP requiere Node.js 18+, `npx`, configurar `mcpServers` en cada perfil, manejar credenciales en .env de servidor externo, y paga esquema por cada herramienta en cada turno. Un CLI es `uv run mudctl <verbo>` — un proceso, un archivo `.env`, sin servidor que mantener.
- **Stack**: Python 3.11+, `uv`, `python-dotenv`, `ftplib` (stdlib). Opcional: `paramiko` para SFTP.
- **Auth**: `.env` con `MUD_HOST`, `MUD_PORT`, `MUD_USER`, `MUD_PASSWORD`, `MUD_PROTOCOL`. Nunca por argumento de CLI.
- **Repo**: `C:/Users/ic_ma/Documents/Desarrollo/GitHub/mudctl/`. Privado por ahora (tiene lógica sensible sobre el servidor de Reinos de Leyenda).

## Reglas de diseño "a prueba de agentes" (el requisito que manda)

La debe usar bien un modelo de gama media sin causar destrozos:

- Verbos explícitos y estrechos (`doctor`, `list`, `get`, `put`, `diff`, `mkdir`, `rm`, `search`, `describe`).
- Toda salida con `--json` de esquema estable + texto plano por defecto. **Exit codes** consistentes.
- Errores **estructurados** y con `hint`, para que un modelo débil se recupere.
- `describe` y `doctor` para que el agente aprenda la herramienta y verifique el entorno.
- `--yes` para confirmar operaciones destructivas, `--expect N` para conteo.
- **dry-run por defecto** en operaciones destructivas.

## YOU MUST — seguridad (innegobiable)

- **NUNCA** commitear credenciales. `.env` (gitignored) o keyring.
- Empezar el repo con `.gitignore` (`.env`, `*.token`, `credentials*.json`) **antes** del primer commit.
- Operaciones destructivas (`rm`/borrar): **dry-run por defecto**. Ejecutar solo con `--yes` y `--expect N` y respetando `--max N`.
- Las credenciales **nunca** se pasan por argumento de CLI (se filtran en `ps`/historial).

## Mantenimiento de doc/estado.md (obligatorio)

`doc/estado.md` es la memoria persistente del proyecto entre sesiones y herramientas.
**Actualizarlo es parte del trabajo**, no opcional:

- Al terminar una sesión de desarrollo o antes de cerrar contexto.
- Al completar cualquier hito (comando nuevo, bug resuelto, decisión técnica importante).
- Al encontrar un problema nuevo o cambiar un plan.
- Si el agente lleva un rato trabajando y detecta que el estado divergió del archivo.

El archivo debe reflejar siempre la realidad del código, no lo que se planeó.
Cualquier modelo que tome el relevo (OpenCode, otra instancia, Opus) debe poder arrancar solo con leer `AGENTS.md` + `doc/estado.md` sin necesidad de explorar el código.

## Repo

- Privado por ahora (tiene lógica sensible sobre el servidor de Reinos de Leyenda).
- Commits y docs en español neutro (sin voseo rioplatense); términos técnicos en inglés está bien.
- Verificación de "hecho": `mudctl doctor` en verde + un listado de directorio + un diff local/remoto que coincidan + un put con dry-run que liste exactamente lo que se subiría sin tocar nada.

## Credenciales FTP (ultimo mensaje conocido)

- Host: `reinosdeleyenda.es`
- Puerto: `3008`
- Usuario: `hazrakh`
- Ultimo mensaje: 24-01-2024 00:56 UTC
- **Advertencia**: Mordisko advirtió el 20/09/2025 que da/quita accesos seguido y considera un riesgo de seguridad tener inmortales inactivos con acceso FTP. Conviene confirmar que siguen operativas antes de usar.
- Archivo de credenciales: `C:/Users/ic_ma/AppData/Local/Temp/mordisco-credencial-ultima.txt`
