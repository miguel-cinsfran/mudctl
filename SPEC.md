# mudctl — Especificación Técnica

## Propósito

CLI para gestionar archivos en el servidor FTP de Reinos de Leyenda. Sirve a agentes de Hermes y a Miguel Ángel desde terminal.

## Stack

Python 3.11+, `uv`, `python-dotenv`, `ftplib` (stdlib). Opcional: `paramiko` para SFTP.

## Estructura del proyecto

```
mudctl/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── AGENTS.md
├── doc/
│   ├── estado.md
│   └── investigacion.md
├── mudctl/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── backend.py
│   ├── commands.py
│   ├── output.py
│   ├── errors.py
│   └── utils.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_doctor.py
    ├── test_list.py
    ├── test_get.py
    ├── test_put.py
    ├── test_diff.py
    ├── test_search.py
    ├── test_rm.py
    ├── test_mkdir.py
    └── test_errors.py
```

## Configuración (env)

Desde `.env` (gitignored) o variables de entorno. Variables:

- `MUD_HOST` — host del servidor FTP. Default: `reinosdeleyenda.es`
- `MUD_PORT` — puerto. Default: `3008`
- `MUD_USER` — usuario. Default: `hazrakh`
- `MUD_PASSWORD` — contraseña. Default: `""`
- `MUD_PROTOCOL` — `ftp`, `ftps` o `sftp`. Default: `ftp`
- `MUD_TIMEOUT` — timeout de conexión en segundos. Default: `30`
- `MUD_ENCODING` — encoding de archivos. Default: `utf-8`
- `MUD_ROOT` — directorio raíz remoto. Default: `/`

Las credenciales nunca se pasan por argumento de CLI.

## Convenciones transversales

### Salida
- Texto plano por defecto (legible con lector de pantalla; sin tablas ASCII).
- `--json` envoltura estable e idéntica en todos los comandos.
- En error: `"ok": false`, `"data": null`, `"error": {"code": "...", "message": "...", "hint": "..."}`.

### Exit codes
| Código | Significado |
|---|---|
| 0 | OK |
| 2 | Error de uso (flags/argumentos) |
| 3 | Error de autenticación/credenciales |
| 4 | Error de red / FTP / SFTP |
| 5 | No encontrado |
| 6 | Abortado por seguridad (p. ej. `--expect` no coincide) |
| 7 | Error interno |

### Verbos
| Verbo | Uso | Description |
|---|---|---|
| `doctor` | `mudctl doctor` | Prueba conexión y autenticación |
| `list` | `mudctl list [ruta] [--recursive] [--depth N]` | Lista archivos y directorios |
| `get` | `mudctl get remote_path [local_path]` | Descarga archivo o directorio |
| `put` | `mudctl put local_path remote_path [--dry-run] [--yes] [--expect N]` | Sube archivo o directorio |
| `diff` | `mudctl diff local_path remote_path` | Compara archivo local vs remoto |
| `search` | `mudctl search patron [ruta] [--regex] [--case-insensitive]` | Busca archivos o contenido |
| `mkdir` | `mudctl mkdir ruta [--parents]` | Crea directorio |
| `rm` | `mudctl rm ruta [--recursive] [--dry-run] [--yes] [--expect N] [--max N]` | Borra archivo o directorio |
| `cat` | `mudctl cat ruta` | Muestra contenido de archivo remoto |
| `info` | `mudctl info ruta` | Muestra metadata (tamaño, fecha, permisos) |
| `move` | `mudctl move origen destino` | Renombra o mueve archivo/directorio |
| `describe` | `mudctl describe` | Muestra ayuda completa |

## Reglas de seguridad

- **NUNCA** commitear credenciales. `.env` (gitignored) o keyring.
- Empezar el repo con `.gitignore` (`.env`, `*.token`, `credentials*.json`) **antes** del primer commit.
- Operaciones destructivas (`rm`/borrar): **dry-run por defecto**. Ejecutar solo con `--yes` y `--expect N` y respetando `--max N`.
- Las credenciales nunca se pasan por argumento de CLI (se filtran en `ps`/historial).
- `--json` salida estable para agentes.
- Errores estructurados con `hint` para recuperación.

## Requisitos (pyproject.toml)

```toml
[project]
name = "mudctl"
version = "0.1.0"
description = "CLI FTP para Reinos de Leyenda — gestión de archivos para agentes"
requires-python = ">=3.11"
dependencies = [
    "python-dotenv>=1.0.0",
]

[project.scripts]
mudctl = "mudctl.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Fases de implementación

1. **Fase cero** — validar: `mudctl doctor` con conexión real, confirmar protocolo (puerto 3008).
2. **MVP** — `doctor`, `list`, `get`, `put`, `diff`, `describe`, `cat`, `info`, `mkdir`, `rm`.
3. **Segunda** — `search`, `move`, `--json`, `--yes`, `--expect`, `--max`, `--dry-run`, `--recursive`, `--depth`.
4. **Luna** — revisión del código antes de primer uso real.

## Archivos relacionados

- `C:/Users/ic_ma/Documents/Desarrollo/GitHub/mailctl/` — referencia de diseño
- `C:/Users/ic_ma/AppData/Local/Temp/mordisco-credencial-ultima.txt` — credenciales FTP
- `C:/Users/ic_ma/Documents/Hermes/skills-compartidas/autonomous-ai-agents/delegar-desarrollo-lorena/` — skill kanban
- `C:/Users/ic_ma/Documents/Hermes/skills-compartidas/devops/vault-guias/` — guías del vault
