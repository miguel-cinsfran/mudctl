from __future__ import annotations

import os
import sys
from ftplib import FTP, error_perm
from pathlib import Path
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()

from mudctl.errors import AuthenticationError, NetworkError, NotFoundError, UsageError
from mudctl.output import Result, OutputFormatter, ExitCode, make_result, make_error


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class FTPBackend(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def list(self, path: str, recursive: bool = False, depth: int | None = None) -> list[dict]:
        pass

    @abstractmethod
    def get(self, remote_path: str, local_path: str) -> dict:
        pass

    @abstractmethod
    def put(self, local_path: str, remote_path: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def diff(self, local_path: str, remote_path: str) -> dict:
        pass

    @abstractmethod
    def search(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False) -> list[dict]:
        pass

    @abstractmethod
    def mkdir(self, path: str, parents: bool = False) -> dict:
        pass

    @abstractmethod
    def rm(self, path: str, recursive: bool = False, dry_run: bool = True, expect: int | None = None, max_files: int | None = None) -> dict:
        pass

    @abstractmethod
    def cat(self, path: str) -> dict:
        pass

    @abstractmethod
    def info(self, path: str) -> dict:
        pass

    @abstractmethod
    def move(self, source: str, destination: str) -> dict:
        pass

    @abstractmethod
    def doctor(self) -> dict:
        pass

    @abstractmethod
    def describe(self) -> str:
        pass


class FTPClientBackend(FTPBackend):
    def __init__(self):
        self._ftp: FTP | None = None
        self._host = _env("MUD_HOST", "reinosdeleyenda.es")
        self._port = int(_env("MUD_PORT", "3008"))
        self._user = _env("MUD_USER", "hazrakh")
        self._password = _env("MUD_PASSWORD", "")
        self._timeout = int(_env("MUD_TIMEOUT", "30"))
        self._encoding = _env("MUD_ENCODING", "utf-8")
        self._root = _env("MUD_ROOT", "/")

    def connect(self) -> bool:
        try:
            self._ftp = FTP()
            self._ftp.connect(self._host, self._port, timeout=self._timeout)
            self._ftp.login(self._user, self._password)
            self._ftp.encoding = self._encoding
            return True
        except error_perm as e:
            raise AuthenticationError(hint="Verifica usuario y contraseña en .env") from e
        except Exception as e:
            raise NetworkError(hint="Verifica host, puerto y conexion de red") from e

    def disconnect(self) -> None:
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                pass
            self._ftp = None

    def _ensure_connected(self):
        if not self._ftp:
            self.connect()

    def doctor(self) -> dict:
        try:
            self.connect()
            self._ftp.sendcmd("NOOP")
            self.disconnect()
            return {"status": "ok", "host": self._host, "port": self._port, "user": self._user, "protocol": "ftp", "message": "Conexion exitosa"}
        except AuthenticationError as e:
            return {"status": "error", "code": "AUTH", "message": str(e.message), "hint": e.hint}
        except NetworkError as e:
            return {"status": "error", "code": "NETWORK", "message": str(e.message), "hint": e.hint}

    def list(self, path: str, recursive: bool = False, depth: int | None = None) -> list[dict]:
        try:
            self._ensure_connected()
            files = []
            self._ftp.retrlines(f"LIST {path}", files.append)
            return [{"raw": f} for f in files]
        except Exception as e:
            return []

    def get(self, remote_path: str, local_path: str | None = None) -> dict:
        try:
            self._ensure_connected()
            if local_path is None:
                local_path = Path(remote_path).name
            with open(local_path, "wb") as f:
                self._ftp.retrbinary(f"RETR {remote_path}", f.write)
            size = os.path.getsize(local_path)
            return {"remote": remote_path, "local": local_path, "bytes": size, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta remota"}

    def put(self, local_path: str, remote_path: str, dry_run: bool = True) -> dict:
        if dry_run:
            return {"action": "dry-run", "local": local_path, "remote": remote_path, "message": f"Se subira: {local_path} -> {remote_path}"}
        try:
            self._ensure_connected()
            with open(local_path, "rb") as f:
                self._ftp.storbinary(f"STOR {remote_path}", f)
            return {"action": "uploaded", "local": local_path, "remote": remote_path, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica el archivo local y la ruta remota"}

    def diff(self, local_path: str, remote_path: str) -> dict:
        try:
            self._ensure_connected()
            local_size = os.path.getsize(local_path) if os.path.exists(local_path) else None
            import io
            remote_file = io.BytesIO()
            self._ftp.retrbinary(f"RETR {remote_path}", remote_file.write)
            remote_size = len(remote_file.getvalue())
            if local_size == remote_size:
                return {"local": local_path, "remote": remote_path, "match": True, "message": "Sin diferencias"}
            return {"local": local_path, "remote": remote_path, "match": False, "local_size": local_size, "remote_size": remote_size}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def search(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False) -> list[dict]:
        try:
            self._ensure_connected()
            files = []
            self._ftp.retrlines(f"LIST {path}", files.append)
            return [{"raw": f} for f in files if pattern.lower() in f.lower()]
        except Exception as e:
            return []

    def mkdir(self, path: str, parents: bool = False) -> dict:
        try:
            self._ensure_connected()
            self._ftp.mkd(path)
            return {"path": path, "created": True, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def rm(self, path: str, recursive: bool = False, dry_run: bool = True, expect: int | None = None, max_files: int | None = None) -> dict:
        if dry_run:
            msg = f"Se borraria: {path}"
            if recursive:
                msg += " (recursivo)"
            return {"action": "dry-run", "path": path, "recursive": recursive, "message": msg}
        try:
            self._ensure_connected()
            if recursive:
                self._ftp.rmd(path)
            else:
                self._ftp.delete(path)
            return {"path": path, "deleted": True, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def cat(self, path: str) -> dict:
        try:
            self._ensure_connected()
            import io
            data = io.BytesIO()
            self._ftp.retrbinary(f"RETR {path}", data.write)
            text = data.getvalue().decode(self._encoding, errors="replace")
            return {"path": path, "content": text, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def info(self, path: str) -> dict:
        try:
            self._ensure_connected()
            import io
            data = io.BytesIO()
            self._ftp.retrbinary(f"SIZE {path}", data.write)
            return {"path": path, "size": len(data.getvalue()), "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def move(self, source: str, destination: str) -> dict:
        try:
            self._ensure_connected()
            import io
            data = io.BytesIO()
            self._ftp.retrbinary(f"RETR {source}", data.write)
            self._ftp.storbinary(f"STOR {destination}", io.BytesIO(data.getvalue()))
            return {"source": source, "destination": destination, "moved": True, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def describe(self) -> str:
        return """mudctl — CLI FTP para Reinos de Leyenda

Uso:
  mudctl doctor
  mudctl list [ruta] [--recursive] [--depth N]
  mudctl get <remote_path> [local_path]
  mudctl put <local_path> <remote_path> [--dry-run] [--yes] [--expect N]
  mudctl diff <local_path> <remote_path>
  mudctl search <patron> [ruta] [--regex] [--case-insensitive]
  mudctl mkdir <ruta> [--parents]
  mudctl rm <ruta> [--recursive] [--dry-run] [--yes] [--expect N] [--max N]
  mudctl cat <ruta>
  mudctl info <ruta>
  mudctl move <origen> <destino>
  mudctl describe

Salida: texto plano por defecto (NVDA), --json para agentes.
Codigos de salida: 0=OK, 2=uso, 3=auth, 4=red, 5=no encontrado, 6=abortado.
"""
