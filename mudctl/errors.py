from __future__ import annotations

import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


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


class FTPBackendError(Exception):
    def __init__(self, code: str, message: str, hint: str):
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(f"[{code}] {message}: {hint}")


class AuthenticationError(FTPBackendError):
    def __init__(self, hint: str = "Verifica usuario y contraseña en .env"):
        super().__init__("AUTH", "Autenticacion fallida", hint)


class NetworkError(FTPBackendError):
    def __init__(self, hint: str = "Verifica host, puerto y conexion de red"):
        super().__init__("NETWORK", "Error de red", hint)


class NotFoundError(FTPBackendError):
    def __init__(self, hint: str = "Verifica que la ruta exista"):
        super().__init__("NOT_FOUND", "No encontrado", hint)


class AbortedError(FTPBackendError):
    def __init__(self, hint: str = "Operacion abortada por seguridad"):
        super().__init__("ABORTED", "Abortado por seguridad", hint)


class UsageError(FTPBackendError):
    def __init__(self, hint: str = "Revisa los argumentos"):
        super().__init__("USAGE", "Error de uso", hint)
