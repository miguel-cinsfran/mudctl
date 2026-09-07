# mudctl — Documentación de la API para Agentes

## Formato de salida JSON

Todos los comandos aceptan `--json` para salida estructurada. El formato JSON sigue este esquema:

### Éxito
```json
{
  "ok": true,
  "command": "doctor",
  "data": {
    "status": "ok",
    "host": "reinosdeleyenda.es",
    "port": 3008,
    "user": "hazrakh",
    "protocol": "ftp",
    "message": "Conexion exitosa"
  }
}
```

### Error
```json
{
  "ok": false,
  "command": "doctor",
  "error": {
    "code": "AUTH",
    "message": "Autenticacion fallida",
    "hint": "Verifica usuario y contraseña en .env"
  }
}
```

## Uso desde agentes de Hermes

```python
# Ejemplo: verificar conexión
import subprocess
result = subprocess.run(["mudctl", "doctor", "--json"], capture_output=True, text=True)
data = json.loads(result.stdout)
if data["ok"]:
    print(f"Conectado a {data['data']['host']}:{data['data']['port']}")
else:
    print(f"Error: {data['error']['message']}")

# Ejemplo: listar archivos
result = subprocess.run(["mudctl", "list", "/zona", "--json"], capture_output=True, text=True)
data = json.loads(result.stdout)
for item in data["data"]:
    print(item["raw"])
```

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Operación exitosa |
| 2 | Uso incorrecto (faltan argumentos) |
| 3 | Error de autenticación |
| 4 | Error de red/conexión |
| 5 | Recurso no encontrado |
| 6 | Operación abortada (expect/max no cumplido) |
| 7 | Error interno |

## Integración con otros componentes

- **Lorena (coding)**: Puede ejecutar mudctl directamente con `terminal` o `code_execution`
- **Diseño**: No aplica, mudctl es CLI puro
- **Mezcla**: No aplica, es un CLI autónomo
- **telegram-admin**: Puede ejecutar mudctl como worker para operaciones FTP
- **cron**: Puede programarse para verificar disponibilidad del FTP periódicamente

## Ejemplo de cron

```yaml
# En profiles/coding/cron/
- name: "mudctl-doctor"
  schedule: "0 */6 * * *"  # Cada 6 horas
  command: "cd /c/Users/ic_ma/Documents/Desarrollo/GitHub/mudctl && uv run mudctl doctor --json"
  output: "local"
  notify: false
```
