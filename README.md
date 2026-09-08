# mudctl — README

## mudctl — CLI FTP para Reinos de Leyenda

Un programa que permite gestionar archivos en el servidor FTP de Reinos de Leyenda desde la terminal. Diseñado para agentes de Hermes y para Miguel Ángel.

## Instalación

```bash
cd C:/Users/ic_ma/Documents/Desarrollo/GitHub/mudctl
uv pip install -e .
```

## Uso rápido

```bash
# Verificar conexión
mudctl doctor

# Ver ayuda completa
mudctl describe

# Listar archivos
mudctl list /zona

# Bajar un archivo
mudctl get /zona/archivo.c archivo.c

# Subir un archivo (dry-run primero)
mudctl put archivo.c /zona/archivo.c --dry-run --expect 1

# Subir un archivo
mudctl put archivo.c /zona/archivo.c --yes

# Comparar archivos locales y remotos
mudctl diff local.c /zona/remote.c

# Buscar archivos
mudctl search "clase" /zona
mudctl search --regex "patron" /zona --case-insensitive

# Crear carpeta
mudctl mkdir /zona/nueva --parents

# Borrar con dry-run
mudctl rm /zona/old.c --dry-run --expect 1

# Leer contenido de un archivo remoto
mudctl cat /zona/README.txt

# Ver info de un archivo
mudctl info /zona/archivo.c

# Mover un archivo remoto
mudctl move /zona/old.c /zona/new.c

# Bajar una carpeta entera de otro inmo
mudctl get /otros/mago ./mago --recursive

# Subir una carpeta entera a tu casa (dry-run primero)
mudctl put ./mipack /hazrakh/mipack --recursive --dry-run
mudctl put ./mipack /hazrakh/mipack --recursive --yes --expect 12

# Copiar dentro del servidor sin bajar nada
mudctl cp /otros/mago/espada.c /hazrakh/espada.c --dry-run
mudctl cp /otros/mago/espada.c /hazrakh/espada.c --yes

# Crear tu versión desde un ejemplo ajeno sin pisar nada
mudctl scaffold /otros/mago/espada.c /hazrakh/mi_espada.c --yes

# Buscar texto dentro de ficheros de otras carpetas
mudctl grep "hereda de" /otros --case-insensitive --max 20

# Comparar tu carpeta local contra la remota
mudctl status ./mipack /hazrakh/mipack

# Aplicar un parche a un fichero remoto
mudctl apply fix.patch /hazrakh/espada.c --dry-run
mudctl apply fix.patch /hazrakh/espada.c --yes

# Validar y aplicar un lote con un solo --yes
mudctl plan cambios.json --dry-run
mudctl plan cambios.json --yes

# Ver la cola de un log y vigilar novedades ajenas
mudctl tail /hazrakh/log.txt --lines 30
mudctl watch /otros/mago
```

## Opciones globales

- `--json`: Salida en JSON para agentes de Hermes
- `--help`: Muestra esta ayuda
- `--dry-run`: Simular sin ejecutar (por defecto en rm, put)
- `--yes`: Confirmar sin preguntar (requiere --expect N)
- `--expect N`: Esperar exactamente N archivos (para operaciones peligrosas)
- `--max N`: Máximo de archivos a afectar

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Operación exitosa |
| 2 | Uso incorrecto |
| 3 | Error de autenticación |
| 4 | Error de red |
| 5 | Recurso no encontrado |
| 6 | Operación abortada |
| 7 | Error interno |

## Configuración

Crea un archivo `.env` en el directorio del proyecto:

```env
MUD_HOST=reinosdeleyenda.es
MUD_PORT=3008
MUD_USER=hazrakh
MUD_PASSWORD=tu_contraseña_aqui
MUD_PROTOCOL=ftp
MUD_TIMEOUT=30
MUD_ENCODING=utf-8
MUD_ROOT=/
```

Nunca subas `.env` a GitHub — está en `.gitignore`.

## Para agentes de Hermes

```python
import subprocess, json

result = subprocess.run(["mudctl", "doctor", "--json"], capture_output=True, text=True)
data = json.loads(result.stdout)
if data["ok"]:
    print(f"Conectado a {data['data']['host']}")
else:
    print(f"Error: {data['error']['message']}")
```

## Estructura del proyecto

```
mudctl/
├── pyproject.toml       # Configuración del proyecto y dependencias
├── .env.example         # Plantilla de variables de entorno
├── .gitignore           # Archivos excluidos de Git
├── mudctl/              # Código fuente
│   ├── __init__.py      # Inicialización del paquete
│   ├── cli.py           # Punto de entrada principal
│   ├── __main__.py      # Ejecutable módulo
│   ├── backend.py       # Backend FTPClientBackend con todos los verbos
│   ├── commands.py      # Dispatcher de comandos y handlers
│   ├── output.py        # Formateo de salida (texto y JSON)
│   ├── errors.py        # Clases de error personalizadas
│   └── utils.py         # Utilidades compartidas
├── tests/               # Pruebas
│   ├── test_core.py     # Tests del núcleo
│   └── test_utils.py    # Tests de utilidades
├── doc/                 # Documentación
│   ├── estado.md        # Estado del proyecto
│   ├── investigacion.md # Investigación sobre protocolo
│   └── api.md           # API para agentes
└── SPEC.md              # Especificación técnica
```

## Licencia

Propiedad de Miguel Ángel Insfrán Caballero. Todos los derechos reservados.
