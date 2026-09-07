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
    def get(self, remote_path: str, local_path: str | None, recursive: bool = False) -> dict:
        pass

    @abstractmethod
    def put(self, local_path: str, remote_path: str, dry_run: bool = True, recursive: bool = False, expect: int | None = None) -> dict:
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
    def cp(self, source: str, destination: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def grep(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False, max_hits: int = 50) -> dict:
        pass

    @abstractmethod
    def scaffold(self, source: str, destination: str, dry_run: bool = True) -> dict:
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
        self._home = _env("MUD_HOME", f"/{self._user}")

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

    def _norm(self, path: str) -> str:
        p = (path or "/").replace("\\", "/")
        if not p.startswith("/"):
            p = "/" + p
        while "//" in p:
            p = p.replace("//", "/")
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p

    def _within_home(self, path: str) -> bool:
        p = self._norm(path)
        home = self._norm(self._home)
        return p == home or p.startswith(home + "/")

    def _writable_error(self, path: str) -> dict | None:
        if not self._within_home(path):
            return {"status": "error", "code": "ABORTED", "message": f"Fuera de tu carpeta ({self._home})", "hint": "Lee donde quieras, pero escribe solo dentro de tu carpeta"}
        return None

    def _child_names(self, path: str) -> list[str]:
        try:
            names = []
            for name, facts in self._ftp.mlsd(path):
                if name not in (".", ".."):
                    names.append(name)
            return names
        except Exception:
            pass
        try:
            return [n for n in self._ftp.nlst(path) if n not in (".", "..")]
        except Exception:
            return []

    def _is_dir(self, path: str) -> bool:
        try:
            cur = self._ftp.pwd()
        except Exception:
            cur = None
        try:
            self._ftp.cwd(path)
            if cur is not None:
                try:
                    self._ftp.cwd(cur)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    def _mkdirs(self, path: str) -> None:
        target = self._norm(path)
        parts = target.strip("/").split("/")
        cur = ""
        for part in parts:
            cur = cur + "/" + part
            try:
                self._ftp.mkd(cur)
            except Exception:
                pass

    def _walk_remote(self, path: str) -> tuple[list[str], list[str]]:
        dirs = [self._norm(path)]
        files: list[str] = []
        seen = {self._norm(path)}
        out_dirs = [self._norm(path)]
        i = 0
        while i < len(dirs):
            cur = dirs[i]
            i += 1
            for name in self._child_names(cur):
                full = self._norm(cur + "/" + name.split("/")[-1])
                if full in seen:
                    continue
                seen.add(full)
                if self._is_dir(full):
                    dirs.append(full)
                    out_dirs.append(full)
                else:
                    files.append(full)
        return out_dirs, files

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

    def get(self, remote_path: str, local_path: str | None = None, recursive: bool = False) -> dict:
        try:
            self._ensure_connected()
            if not recursive:
                if local_path is None:
                    local_path = Path(remote_path).name
                with open(local_path, "wb") as f:
                    self._ftp.retrbinary(f"RETR {remote_path}", f.write)
                size = os.path.getsize(local_path)
                return {"remote": remote_path, "local": local_path, "bytes": size, "status": "ok"}
            base = self._norm(remote_path)
            dest_base = Path(local_path) if local_path else Path(Path(base).name)
            _dirs, files = self._walk_remote(base)
            count = 0
            total = 0
            for rf in files:
                rel = rf[len(base):].lstrip("/")
                lp = dest_base / rel
                lp.parent.mkdir(parents=True, exist_ok=True)
                with open(lp, "wb") as f:
                    self._ftp.retrbinary(f"RETR {rf}", f.write)
                total += os.path.getsize(lp)
                count += 1
            return {"remote": base, "local": str(dest_base), "files": count, "bytes": total, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta remota"}

    def put(self, local_path: str, remote_path: str, dry_run: bool = True, recursive: bool = False, expect: int | None = None) -> dict:
        werr = self._writable_error(remote_path)
        if werr:
            return werr
        lp = Path(local_path)
        if recursive and lp.is_dir():
            files = sorted([p for p in lp.rglob("*") if p.is_file()])
            if expect is not None and expect != len(files):
                return {"status": "error", "code": "ABORTED", "message": f"Expect {expect} no coincide con {len(files)}", "hint": "Revisa --expect"}
            if dry_run:
                return {"status": "ok", "action": "dry-run", "local": local_path, "remote": remote_path, "files": len(files), "message": f"Se subirian {len(files)} ficheros: {local_path} -> {remote_path}"}
            try:
                self._ensure_connected()
                base = self._norm(remote_path)
                self._mkdirs(base)
                for p in files:
                    rel = p.relative_to(lp).as_posix()
                    rd = self._norm(base + "/" + rel)
                    parent = "/" + "/".join(rd.strip("/").split("/")[:-1])
                    if parent and parent != "/":
                        self._mkdirs(parent)
                    self._ftp.storbinary(f"STOR {rd}", open(p, "rb"))
                return {"status": "ok", "action": "uploaded", "local": local_path, "remote": remote_path, "files": len(files)}
            except Exception as e:
                return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica el archivo local y la ruta remota"}
        if dry_run:
            return {"status": "ok", "action": "dry-run", "local": local_path, "remote": remote_path, "message": f"Se subira: {local_path} -> {remote_path}"}
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
                return {"status": "ok", "local": local_path, "remote": remote_path, "match": True, "message": "Sin diferencias"}
            return {"status": "ok", "local": local_path, "remote": remote_path, "match": False, "local_size": local_size, "remote_size": remote_size}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def search(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False) -> list[dict]:
        try:
            self._ensure_connected()
            files = []
            self._ftp.retrlines(f"LIST {path}", files.append)
            if regex:
                import re
                flags = re.IGNORECASE if case_insensitive else 0
                rx = re.compile(pattern, flags)
                return [{"raw": f} for f in files if rx.search(f)]
            if case_insensitive:
                return [{"raw": f} for f in files if pattern.lower() in f.lower()]
            return [{"raw": f} for f in files if pattern in f]
        except Exception as e:
            return []

    def mkdir(self, path: str, parents: bool = False) -> dict:
        werr = self._writable_error(path)
        if werr:
            return werr
        try:
            self._ensure_connected()
            if not parents:
                self._ftp.mkd(path)
                return {"path": path, "created": True, "status": "ok"}
            target = self._norm(path)
            parts = target.strip("/").split("/")
            cur = ""
            for part in parts:
                cur = cur + "/" + part
                try:
                    self._ftp.mkd(cur)
                except Exception:
                    pass
            return {"path": target, "created": True, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def rm(self, path: str, recursive: bool = False, dry_run: bool = True, expect: int | None = None, max_files: int | None = None) -> dict:
        count = 1
        if expect is not None and expect != count:
            return {"status": "error", "code": "ABORTED", "message": f"Expect {expect} no coincide con {count}", "hint": "Revisa --expect"}
        if max_files is not None and count > max_files:
            return {"status": "error", "code": "ABORTED", "message": f"Supera --max {max_files}", "hint": "Sube --max o reduce el alcance"}
        if dry_run:
            msg = f"Se borraria: {path}"
            if recursive:
                msg += " (recursivo)"
            return {"status": "ok", "action": "dry-run", "path": path, "recursive": recursive, "message": msg}
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
            size = self._ftp.size(path)
            return {"path": path, "size": size, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def move(self, source: str, destination: str) -> dict:
        werr = self._writable_error(destination)
        if werr:
            return werr
        try:
            self._ensure_connected()
            self._ftp.rename(source, destination)
            return {"source": source, "destination": destination, "moved": True, "status": "ok"}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def cp(self, source: str, destination: str, dry_run: bool = True) -> dict:
        werr = self._writable_error(destination)
        if werr:
            return werr
        try:
            self._ensure_connected()
            if self._is_dir(source):
                _dirs, files = self._walk_remote(source)
                base = self._norm(source)
                dest = self._norm(destination)
                if dry_run:
                    return {"status": "ok", "action": "dry-run", "source": base, "destination": dest, "files": len(files), "message": f"Se copiarian {len(files)} ficheros: {base} -> {dest}"}
                import io
                self._mkdirs(dest)
                for rf in files:
                    rel = rf[len(base):].lstrip("/")
                    rd = self._norm(dest + "/" + rel)
                    parent = "/" + "/".join(rd.strip("/").split("/")[:-1])
                    if parent and parent != "/":
                        self._mkdirs(parent)
                    buf = io.BytesIO()
                    self._ftp.retrbinary(f"RETR {rf}", buf.write)
                    buf.seek(0)
                    self._ftp.storbinary(f"STOR {rd}", buf)
                return {"status": "ok", "action": "copied", "source": base, "destination": dest, "files": len(files)}
            import io
            if dry_run:
                return {"status": "ok", "action": "dry-run", "source": source, "destination": destination, "message": f"Se copiaria: {source} -> {destination}"}
            buf = io.BytesIO()
            self._ftp.retrbinary(f"RETR {source}", buf.write)
            buf.seek(0)
            self._ftp.storbinary(f"STOR {destination}", buf)
            return {"status": "ok", "action": "copied", "source": source, "destination": destination}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def grep(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False, max_hits: int = 50) -> dict:
        try:
            self._ensure_connected()
            import io
            import re
            _dirs, files = self._walk_remote(path)
            flags = re.IGNORECASE if case_insensitive else 0
            rx = re.compile(pattern, flags) if regex else None
            needle = pattern.lower() if case_insensitive and not regex else pattern
            hits: list[dict] = []
            scanned = 0
            for rf in files:
                if len(hits) >= max_hits:
                    break
                try:
                    buf = io.BytesIO()
                    self._ftp.retrbinary(f"RETR {rf}", buf.write)
                    raw = buf.getvalue()
                    if len(raw) > 2 * 1024 * 1024:
                        continue
                    text = raw.decode(self._encoding, errors="replace")
                except Exception:
                    continue
                scanned += 1
                for i, line in enumerate(text.splitlines(), 1):
                    if len(hits) >= max_hits:
                        break
                    found = bool(rx.search(line)) if rx else (needle in line.lower() if case_insensitive else needle in line)
                    if found:
                        hits.append({"path": rf, "line": i, "text": line[:300]})
            return {"status": "ok", "pattern": pattern, "path": path, "scanned": scanned, "hits": hits}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def scaffold(self, source: str, destination: str, dry_run: bool = True) -> dict:
        werr = self._writable_error(destination)
        if werr:
            return werr
        try:
            self._ensure_connected()
            if self._is_dir(destination):
                return {"status": "error", "code": "ABORTED", "message": f"Destino ya existe: {destination}", "hint": "Elegi otro nombre para no pisar tu trabajo"}
            try:
                self._ftp.size(destination)
                return {"status": "error", "code": "ABORTED", "message": f"Destino ya existe: {destination}", "hint": "Elegi otro nombre para no pisar tu trabajo"}
            except Exception:
                pass
            return self.cp(source, destination, dry_run=dry_run)
        except Exception as e:
            err = str(e)
            if "ya existe" in err:
                return {"status": "error", "code": "ABORTED", "message": err, "hint": "Elegi otro nombre"}
            return {"status": "error", "code": "NETWORK", "message": err, "hint": "Verifica las rutas"}

    def describe(self) -> str:
        return """mudctl — CLI FTP para Reinos de Leyenda

Uso:
  mudctl doctor
  mudctl list [ruta] [--recursive] [--depth N]
  mudctl get <remote_path> [local_path] [--recursive]
  mudctl put <local_path> <remote_path> [--dry-run] [--yes] [--expect N] [--recursive]
  mudctl diff <local_path> <remote_path>
  mudctl search <patron> [ruta] [--regex] [--case-insensitive]
  mudctl grep <patron> [ruta] [--regex] [--case-insensitive] [--max N]
  mudctl mkdir <ruta> [--parents]
  mudctl rm <ruta> [--recursive] [--dry-run] [--yes] [--expect N] [--max N]
  mudctl cat <ruta>
  mudctl info <ruta>
  mudctl move <origen> <destino>
  mudctl cp <origen> <destino> [--dry-run] [--yes]
  mudctl scaffold <ejemplo> <destino-nuevo> [--dry-run] [--yes]
  mudctl describe

Salida: texto plano por defecto (NVDA), --json para agentes.
Codigos de salida: 0=OK, 2=uso, 3=auth, 4=red, 5=no encontrado, 6=abortado.
"""
