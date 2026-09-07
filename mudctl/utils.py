from __future__ import annotations

import os
import sys


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config() -> dict[str, str]:
    """Carga la configuracion desde .env o variables de entorno."""
    return {
        "host": _env("MUD_HOST", "reinosdeleyenda.es"),
        "port": int(_env("MUD_PORT", "3008")),
        "user": _env("MUD_USER", "hazrakh"),
        "password": _env("MUD_PASSWORD", ""),
        "protocol": _env("MUD_PROTOCOL", "ftp"),
        "timeout": int(_env("MUD_TIMEOUT", "30")),
        "encoding": _env("MUD_ENCODING", "utf-8"),
        "root": _env("MUD_ROOT", "/"),
        "home": _env("MUD_HOME", f"/{_env('MUD_USER', 'hazrakh')}"),
    }


def get_config(key: str, default: str = "") -> str:
    return _env(key, default)


def require_credential(field: str) -> str:
    """Verifica que una credencial este presente."""
    value = _env(f"MUD_{field.upper()}", "")
    if not value:
        from mudctl.errors import AuthenticationError
        raise AuthenticationError(f"Credencial {field} faltante en .env")
    return value
