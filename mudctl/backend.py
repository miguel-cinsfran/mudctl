from __future__ import annotations

import os
import sys
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()

from mudctl.errors import AuthenticationError, NetworkError, NotFoundError, UsageError
from mudctl.output import Result, OutputFormatter, ExitCode, make_result, make_error


class _FTPSReuse(FTP_TLS):
    """FTP_TLS que reutiliza la sesion SSL en conexiones de datos.

    vsFTPd con require_ssl_reuse=YES (como rlmud.org) rechaza LIST/RETR/STOR
    con '522 SSL connection failed: session reuse required' si no se hace.
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


LPC_EXTS = {".c", ".h"}


def _lpc_ok(path: str) -> bool:
    return Path(path).suffix.lower() in LPC_EXTS


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
    def mkdir(self, path: str, parents: bool = False, dry_run: bool = True) -> dict:
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
    def move(self, source: str, destination: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def cp(self, source: str, destination: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def grep(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False, max_hits: int = 50, all_files: bool = False) -> dict:
        pass

    @abstractmethod
    def scaffold(self, source: str, destination: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def status(self, local_base: str, remote_path: str, all_files: bool = False, max_bytes: int = 5 * 1024 * 1024) -> dict:
        pass

    @abstractmethod
    def tail(self, path: str, lines: int = 30) -> dict:
        pass

    @abstractmethod
    def watch(self, path: str, snapshot_file: str | None = None) -> dict:
        pass

    @abstractmethod
    def apply(self, patch_file: str, remote_path: str, dry_run: bool = True) -> dict:
        pass

    @abstractmethod
    def plan(self, ops: list[dict], dry_run: bool = True) -> dict:
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
        self._protocol = _env("MUD_PROTOCOL", "ftp").lower()

    def connect(self) -> bool:
        try:
            if self._protocol == "ftps":
                ftps = _FTPSReuse()
                ftps.connect(self._host, self._port, timeout=self._timeout)
                ftps.login(self._user, self._password)
                ftps.prot_p()
                self._ftp = ftps
            else:
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
            return {"status": "ok", "host": self._host, "port": self._port, "user": self._user, "protocol": self._protocol, "message": "Conexion exitosa"}
        except AuthenticationError as e:
            return {"status": "error", "code": "AUTH", "message": str(e.message), "hint": e.hint}
        except NetworkError as e:
            return {"status": "error", "code": "NETWORK", "message": str(e.message), "hint": e.hint}

    def list(self, path: str, recursive: bool = False, depth: int | None = None) -> list[dict]:
        try:
            self._ensure_connected()
            files = []
            base = self._norm(path)
            try:
                # vsFTPd responde "LIST <dir>" con la entrada del propio dir:
                # entrar y listar sin args trae los hijos de verdad.
                self._ftp.cwd(base)
                self._ftp.retrlines("LIST", files.append)
            except Exception:
                files = []
                self._ftp.retrlines(f"LIST {base}", files.append)
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

    def mkdir(self, path: str, parents: bool = False, dry_run: bool = True) -> dict:
        werr = self._writable_error(path)
        if werr:
            return werr
        if dry_run:
            return {"status": "ok", "action": "dry-run", "path": path, "parents": parents, "message": f"Se crearia: {path}"}
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
        werr = self._writable_error(path)
        if werr:
            return werr
        target = self._norm(path)
        if recursive:
            try:
                self._ensure_connected()
                dirs, files = self._walk_remote(target)
                count = len(files)
            except Exception as e:
                return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}
            if expect is not None and expect != count:
                return {"status": "error", "code": "ABORTED", "message": f"Expect {expect} no coincide con {count}", "hint": "Revisa --expect"}
            if max_files is not None and count > max_files:
                return {"status": "error", "code": "ABORTED", "message": f"Supera --max {max_files}", "hint": "Sube --max o reduce el alcance"}
            if dry_run:
                return {"status": "ok", "action": "dry-run", "path": target, "recursive": True, "files": count, "message": f"Se borrarian {count} ficheros bajo {target}"}
            try:
                for rf in files:
                    self._ftp.delete(rf)
                for d in sorted(dirs[1:], reverse=True):
                    try:
                        self._ftp.rmd(d)
                    except Exception:
                        pass
                try:
                    self._ftp.rmd(target)
                except Exception:
                    pass
                return {"path": target, "deleted": True, "files": count, "status": "ok"}
            except Exception as e:
                return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}
        count = 1
        if expect is not None and expect != count:
            return {"status": "error", "code": "ABORTED", "message": f"Expect {expect} no coincide con {count}", "hint": "Revisa --expect"}
        if max_files is not None and count > max_files:
            return {"status": "error", "code": "ABORTED", "message": f"Supera --max {max_files}", "hint": "Sube --max o reduce el alcance"}
        if dry_run:
            return {"status": "ok", "action": "dry-run", "path": path, "recursive": False, "message": f"Se borraria: {path}"}
        try:
            self._ensure_connected()
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

    def move(self, source: str, destination: str, dry_run: bool = True) -> dict:
        werr = self._writable_error(destination)
        if werr:
            return werr
        if dry_run:
            return {"status": "ok", "action": "dry-run", "source": source, "destination": destination, "message": f"Se moveria: {source} -> {destination}"}
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

    def grep(self, pattern: str, path: str, regex: bool = False, case_insensitive: bool = False, max_hits: int = 50, all_files: bool = False) -> dict:
        try:
            self._ensure_connected()
            import io
            import re
            _dirs, files = self._walk_remote(path)
            if not all_files:
                files = [f for f in files if _lpc_ok(f)]
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

    def status(self, local_base: str, remote_path: str, all_files: bool = False, max_bytes: int = 5 * 1024 * 1024) -> dict:
        try:
            self._ensure_connected()
            import hashlib
            import io
            base = self._norm(remote_path)
            _dirs, files = self._walk_remote(base)
            if not all_files:
                files = [f for f in files if _lpc_ok(f)]
            lb = Path(local_base)
            remote_set = {f[len(base):].lstrip("/") for f in files}
            local_map: dict[str, Path] = {}
            if lb.is_dir():
                for p in lb.rglob("*"):
                    if p.is_file():
                        rel = p.relative_to(lb).as_posix()
                        if all_files or _lpc_ok(rel):
                            local_map[rel] = p
            same, changed, only_local, only_remote, skipped = [], [], [], [], []
            for rf in files:
                rel = rf[len(base):].lstrip("/")
                lp = local_map.get(rel)
                if lp is None:
                    only_remote.append(rel)
                    continue
                try:
                    buf = io.BytesIO()
                    self._ftp.retrbinary(f"RETR {rf}", buf.write)
                    raw = buf.getvalue()
                except Exception:
                    skipped.append(rel)
                    continue
                if len(raw) > max_bytes:
                    skipped.append(rel)
                    continue
                rh = hashlib.sha256(raw).hexdigest()
                lh = hashlib.sha256(lp.read_bytes()).hexdigest()
                (same if rh == lh else changed).append(rel)
            for rel in local_map:
                if rel not in remote_set:
                    only_local.append(rel)
            return {"status": "ok", "remote": base, "local": str(lb), "same": sorted(same), "changed": sorted(changed), "only_local": sorted(only_local), "only_remote": sorted(only_remote), "skipped": sorted(skipped)}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def tail(self, path: str, lines: int = 30) -> dict:
        try:
            self._ensure_connected()
            import io
            buf = io.BytesIO()
            self._ftp.retrbinary(f"RETR {path}", buf.write)
            text = buf.getvalue().decode(self._encoding, errors="replace")
            all_lines = text.splitlines()
            return {"status": "ok", "path": path, "lines": all_lines[-lines:], "total": len(all_lines)}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

    def watch(self, path: str, snapshot_file: str | None = None) -> dict:
        import json
        try:
            self._ensure_connected()
            snap = snapshot_file or ".mudctl-watch.json"
            base = self._norm(path)
            _dirs, files = self._walk_remote(base)
            current = sorted(files)
            old = []
            try:
                old = json.loads(Path(snap).read_text(encoding="utf-8")).get(base, [])
            except Exception:
                pass
            old_set, cur_set = set(old), set(current)
            result = {"status": "ok", "path": base, "new": sorted(cur_set - old_set), "gone": sorted(old_set - cur_set), "snapshot": snap}
            try:
                data = {}
                try:
                    data = json.loads(Path(snap).read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                data[base] = current
                Path(snap).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                result["snapshot_warning"] = str(e)[:120]
            return result
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica la ruta"}

# ---- Sync: manifiesto, locks, y paralelismo ----

    def _manifest_path(self) -> str:
        home = Path(self._home)
        if not home.exists():
            return str(Path.cwd() / ".mudctl-sync.json")
        return str(home / ".mudctl-sync.json")

    def _lock_path(self) -> str:
        home = Path(self._home)
        if not home.exists():
            return str(Path.cwd() / ".mudctl-sync.lock")
        return str(home / ".mudctl-sync.lock")

    def _manifest_load(self) -> dict:
        import json
        p = self._manifest_path()
        try:
            return json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            return {"remote": self._home, "files": {}, "updated": "", "last_run": {}}

    def _manifest_save(self, manifest: dict) -> None:
        import json, os as _os
        p = self._manifest_path()
        tmp = p + ".tmp"
        Path(tmp).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        _os.replace(tmp, p)

    def _lock_acquire(self) -> bool:
        import os
        p = self._lock_path()
        if Path(p).exists():
            try:
                pid = int(Path(p).read_text(encoding="utf-8").strip())
                os.kill(pid, 0)
                return False
            except Exception:
                pass
        Path(p).write_text(str(os.getpid()), encoding="utf-8")
        return True

    def _lock_release(self) -> None:
        import os
        p = self._lock_path()
        try:
            if Path(p).exists() and int(Path(p).read_text(encoding="utf-8").strip()) == os.getpid():
                Path(p).unlink()
        except Exception:
            pass

    def _parse_list_line(self, line: str) -> dict | None:
        import re
        m = re.match(
            r"^([dlrwxcst-]{10})\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(\S+\s+\S+\s+\S+|\S+\s+\S+:\S+)\s+(\S+)(?:\s+->\s+(.+))?$",
            line.strip(),
        )
        if not m:
            return None
        perms, size, mtime, name, target = m.groups()
        ftype = "dir" if perms.startswith("d") else ("link" if perms.startswith("l") else "file")
        return {"name": name, "type": ftype, "size": int(size), "mtime": mtime}

    def _list_lines(self, path: str) -> list[str]:
        self._ensure_connected()
        base = self._norm(path)
        lines: list[str] = []
        try:
            self._ftp.cwd(base)
            self._ftp.retrlines("LIST", lines.append)
        except Exception:
            pass
        return lines

    def _parse_manifest_list(self, path: str) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for line in self._list_lines(path):
            parsed = self._parse_list_line(line)
            if parsed:
                result[parsed["name"]] = {"size": parsed["size"], "mtime": parsed["mtime"], "type": parsed["type"]}
        return result

    def sync_status(self, local_path: str, remote_path: str) -> dict:
        try:
            self._ensure_connected()
            base = self._norm(remote_path)
            manifest = self._manifest_load()
            remote_files = self._parse_manifest_list(base)
            if not manifest.get("files"):
                return {"status": "ok", "local": local_path, "remote": base, "new": list(remote_files.keys()), "changed": [], "gone": [], "message": "Manifiesto vacío: inicializar con sync pull"}
            local_lp = Path(local_path)
            local_map: dict[str, Path] = {}
            if local_lp.is_dir():
                for p in local_lp.rglob("*"):
                    if p.is_file():
                        local_map[p.relative_to(local_lp).as_posix()] = p
            new, changed, gone, same = [], [], [], []
            for name, info in remote_files.items():
                lp = local_map.get(name)
                if lp is None:
                    new.append(name)
                elif lp.is_file():
                    lsize = lp.stat().st_size
                    if lsize != info["size"]:
                        changed.append(name)
                    else:
                        same.append(name)
            for name in local_map:
                if name not in remote_files:
                    gone.append(name)
            return {"status": "ok", "local": local_path, "remote": base, "new": sorted(new), "changed": sorted(changed), "gone": sorted(gone), "same": sorted(same)}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def sync_pull(self, remote_path: str, local_path: str, dry_run: bool = True, parallel: int = 4, expect: int | None = None, prune: bool = False, yes: bool = False) -> dict:
        import json
        import time
        from concurrent.futures import ThreadPoolExecutor
        from datetime import datetime, timezone
        if not dry_run and not yes:
            return {"status": "error", "code": "USAGE", "message": "sync pull necesita --yes para escribir", "hint": "Usa --dry-run para ver qué bajaría"}
        if not self._lock_acquire():
            return {"status": "error", "code": "ABORTED", "message": "Otro sync está activo", "hint": "Espera o mata el proceso lock"}
        try:
            self._ensure_connected()
            base = self._norm(remote_path)
            dest = Path(local_path)
            manifest = self._manifest_load()
            remote_files = self._parse_manifest_list(base)
            old_files = manifest.get("files", {})
            new, changed, same, gone = [], [], [], []
            for name, info in remote_files.items():
                old = old_files.get(name, {})
                if not old:
                    new.append(name)
                elif old.get("size") != info["size"] or old.get("mtime") != info["mtime"]:
                    changed.append(name)
                else:
                    same.append(name)
            for name in old_files:
                if name not in remote_files:
                    gone.append(name)
            to_download = new + changed
            if expect is not None and len(to_download) != expect:
                return {"status": "error", "code": "USAGE", "message": f"Expect {expect} no coincide con {len(to_download)}", "hint": "Revisa --expect"}
            if dry_run:
                return {"status": "ok", "action": "dry-run", "remote": base, "local": str(dest), "new": len(new), "changed": len(changed), "same": len(same), "gone": len(gone), "to_download": len(to_download), "message": f"Dry-run: {len(to_download)} ficheros a bajar"}
            count = 0; bytes_total = 0
            with ThreadPoolExecutor(max_workers=min(parallel, 8)) as pool:
                futures = {}
                for name in to_download:
                    info = remote_files[name]
                    rpath = f"{base}/{name}" if base != "/" else f"/{name}"
                    lpath = dest / name
                    lpath.parent.mkdir(parents=True, exist_ok=True)
                    futures[pool.submit(self._ftp.retrbinary, f"RETR {rpath}", lpath)] = name
                for future in futures:
                    name = futures[future]
                    try:
                        future.result()
                        count += 1
                    except Exception as e:
                        return {"status": "error", "code": "NETWORK", "message": f"Falló {name}: {e}", "hint": "Verifica conexión"}
            for name in to_download:
                info = remote_files[name]
                rpath = f"{base}/{name}" if base != "/" else f"/{name}"
                lpath = dest / name
                if lpath.is_file() and lpath.stat().st_size != info["size"]:
                    return {"status": "error", "code": "ABORTED", "message": f"SIZE mismatch en {name}", "hint": "El fichero descargado no coincide"}
                bytes_total += info["size"]
            if prune:
                for name in gone:
                    lpath = dest / name
                    if lpath.is_file():
                        lpath.unlink()
            new_manifest = {"remote": base, "files": {n: {"size": remote_files[n]["size"], "mtime": remote_files[n]["mtime"]} for n in remote_files}, "updated": datetime.now(timezone.utc).isoformat(), "last_run": {"verb": "pull", "counts": {"new": len(new), "changed": len(changed), "same": len(same), "gone": len(gone)}}}
            self._manifest_save(new_manifest)
            return {"status": "ok", "action": "pulled", "remote": base, "local": str(dest), "files": count, "bytes": bytes_total, "new": len(new), "changed": len(changed), "same": len(same), "gone": len(gone)}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}
        finally:
            self._lock_release()

    def sync_push(self, local_path: str, remote_path: str, dry_run: bool = True, expect: int | None = None, yes: bool = False) -> dict:
        import json
        from datetime import datetime, timezone
        if not dry_run and not yes:
            return {"status": "error", "code": "USAGE", "message": "sync push necesita --yes para escribir", "hint": "Usa --dry-run para ver qué subiría"}
        if not self._lock_acquire():
            return {"status": "error", "code": "ABORTED", "message": "Otro sync está activo", "hint": "Espera o mata el proceso lock"}
        try:
            self._ensure_connected()
            base = self._norm(remote_path)
            dest = Path(local_path)
            manifest = self._manifest_load()
            remote_files = self._parse_manifest_list(base)
            old_files = manifest.get("files", {})
            local_map: dict[str, Path] = {}
            if dest.is_dir():
                for p in dest.rglob("*"):
                    if p.is_file():
                        local_map[p.relative_to(dest).as_posix()] = p
            local_changed = []
            for name, lp in local_map.items():
                old = old_files.get(name, {})
                if not old or lp.stat().st_size != old.get("size", 0):
                    local_changed.append(name)
            remote_changed = []
            for name in old_files:
                if name in remote_files:
                    rinfo = remote_files[name]
                    old_info = old_files[name]
                    if rinfo["size"] != old_info["size"] or rinfo["mtime"] != old_info["mtime"]:
                        remote_changed.append(name)
            conflict = set(local_changed) & set(remote_changed)
            if conflict:
                return {"status": "error", "code": "ABORTED", "message": f"Conflicto en: {sorted(conflict)}", "hint": "Cambiado en ambos lados. Resolve manualmente.", "conflicts": sorted(conflict)}
            if expect is not None and len(local_changed) != expect:
                return {"status": "error", "code": "USAGE", "message": f"Expect {expect} no coincide con {len(local_changed)}", "hint": "Revisa --expect"}
            if dry_run:
                return {"status": "ok", "action": "dry-run", "local": str(dest), "remote": base, "to_upload": len(local_changed), "conflicts": sorted(conflict), "message": f"Dry-run: {len(local_changed)} ficheros a subir"}
            count = 0; bytes_total = 0
            for name in local_changed:
                lp = local_map[name]
                rpath = f"{base}/{name}" if base != "/" else f"/{name}"
                self._ftp.storbinary(f"STOR {rpath}", open(lp, "rb"))
                count += 1
                bytes_total += lp.stat().st_size
            for name in local_changed:
                lp = local_map[name]
                old_files[name] = {"size": lp.stat().st_size, "mtime": datetime.now(timezone.utc).isoformat()}
            new_manifest = {"remote": base, "files": old_files, "updated": datetime.now(timezone.utc).isoformat(), "last_run": {"verb": "push", "counts": {"uploaded": count}}}
            self._manifest_save(new_manifest)
            return {"status": "ok", "action": "pushed", "local": str(dest), "remote": base, "files": count, "bytes": bytes_total, "conflicts": sorted(conflict)}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}
        finally:
            self._lock_release()

    @staticmethod
    def _apply_unified(original: str, patch_text: str) -> str:
        import re
        src = original.splitlines(keepends=False)
        out: list[str] = []
        lines = patch_text.splitlines()
        i = 0
        src_i = 0
        hunk = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        while i < len(lines):
            line = lines[i]
            if line.startswith("---") or line.startswith("+++"):
                i += 1
                continue
            m = hunk.match(line)
            if not m:
                i += 1
                continue
            start = int(m.group(1))
            while src_i < start - 1:
                out.append(src[src_i])
                src_i += 1
            i += 1
            while i < len(lines) and not lines[i].startswith("@@"):
                h = lines[i]
                if h.startswith(" ") or h == "":
                    if src_i >= len(src) or src[src_i] != h[1:]:
                        raise ValueError(f"Contexto no calza en línea {src_i + 1}")
                    out.append(src[src_i])
                    src_i += 1
                elif h.startswith("-"):
                    if src_i >= len(src) or src[src_i] != h[1:]:
                        raise ValueError(f"Borrado no calza en línea {src_i + 1}")
                    src_i += 1
                elif h.startswith("+"):
                    out.append(h[1:])
                elif h.startswith("\\"):
                    pass
                else:
                    raise ValueError(f"Línea de parche desconocida: {h[:40]}")
                i += 1
        while src_i < len(src):
            out.append(src[src_i])
            src_i += 1
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        return text

    def apply(self, patch_file: str, remote_path: str, dry_run: bool = True) -> dict:
        werr = self._writable_error(remote_path)
        if werr:
            return werr
        try:
            patch_text = Path(patch_file).read_text(encoding="utf-8")
        except Exception as e:
            return {"status": "error", "code": "USAGE", "message": f"No pude leer el parche: {e}", "hint": "Revisa la ruta del fichero de parche"}
        try:
            self._ensure_connected()
            import io
            buf = io.BytesIO()
            self._ftp.retrbinary(f"RETR {remote_path}", buf.write)
            original = buf.getvalue().decode(self._encoding, errors="replace")
            try:
                new_text = self._apply_unified(original, patch_text)
            except ValueError as e:
                return {"status": "error", "code": "ABORTED", "message": f"El parche no calza: {e}", "hint": "Regenera el parche contra la versión actual del fichero"}
            hunks = sum(1 for l in patch_text.splitlines() if l.startswith("@@"))
            if dry_run:
                return {"status": "ok", "action": "dry-run", "remote": remote_path, "hunks": hunks, "message": f"Se aplicarian {hunks} bloques en {remote_path}"}
            self._ftp.storbinary(f"STOR {remote_path}", io.BytesIO(new_text.encode(self._encoding)))
            return {"status": "ok", "action": "applied", "remote": remote_path, "hunks": hunks}
        except Exception as e:
            return {"status": "error", "code": "NETWORK", "message": str(e), "hint": "Verifica las rutas"}

    def plan(self, ops: list[dict], dry_run: bool = True) -> dict:
        steps: list[dict] = []
        for n, op in enumerate(ops, 1):
            verb = str(op.get("verb", "")).lower()
            try:
                if verb == "put":
                    r = self.put(op["local"], op["remote"], dry_run=True, recursive=bool(op.get("recursive", False)), expect=op.get("expect"))
                elif verb == "cp":
                    r = self.cp(op["source"], op["destination"], dry_run=True)
                elif verb == "rm":
                    r = self.rm(op["path"], recursive=bool(op.get("recursive", False)), dry_run=True, expect=op.get("expect"), max_files=op.get("max"))
                elif verb == "mkdir":
                    r = self.mkdir(op["path"], parents=bool(op.get("parents", True)), dry_run=True)
                elif verb == "move":
                    r = self.move(op["source"], op["destination"], dry_run=True)
                elif verb == "scaffold":
                    r = self.scaffold(op["source"], op["destination"], dry_run=True)
                elif verb == "apply":
                    r = self.apply(op["patch"], op["remote"], dry_run=True)
                else:
                    r = {"status": "error", "code": "USAGE", "message": f"Verbo no soportado en plan: {verb}", "hint": "Usa put, cp, rm, mkdir, move, scaffold o apply"}
            except KeyError as e:
                r = {"status": "error", "code": "USAGE", "message": f"Falta campo {e} en el paso {n}", "hint": "Revisa el plan.json"}
            steps.append({"step": n, "verb": verb, "result": r})
            if r.get("status") != "ok":
                return {"status": "error", "code": r.get("code", "ABORTED"), "message": f"El plan frena en el paso {n}", "hint": "Corrige el paso y revalida", "steps": steps}
        if dry_run:
            return {"status": "ok", "action": "dry-run", "steps": steps, "message": f"Plan válido con {len(steps)} pasos"}
        done: list[dict] = []
        for s in steps:
            n, verb, op = s["step"], s["verb"], ops[s["step"] - 1]
            if verb == "put":
                r = self.put(op["local"], op["remote"], dry_run=False, recursive=bool(op.get("recursive", False)), expect=op.get("expect"))
            elif verb == "cp":
                r = self.cp(op["source"], op["destination"], dry_run=False)
            elif verb == "rm":
                r = self.rm(op["path"], recursive=bool(op.get("recursive", False)), dry_run=False, expect=op.get("expect"), max_files=op.get("max"))
            elif verb == "mkdir":
                r = self.mkdir(op["path"], parents=bool(op.get("parents", True)), dry_run=False)
            elif verb == "move":
                r = self.move(op["source"], op["destination"], dry_run=False)
            elif verb == "scaffold":
                r = self.scaffold(op["source"], op["destination"], dry_run=False)
            elif verb == "apply":
                r = self.apply(op["patch"], op["remote"], dry_run=False)
            done.append({"step": n, "verb": verb, "result": r})
            if r.get("status") != "ok":
                return {"status": "error", "code": r.get("code", "NETWORK"), "message": f"El plan frenó en el paso {n}", "hint": "Lo anterior ya se aplicó, revisa el estado", "done": done}
        return {"status": "ok", "action": "applied", "done": done}

    def describe(self) -> str:
        return """mudctl — CLI FTP para Reinos de Leyenda

Uso:
  mudctl doctor
  mudctl list [ruta] [--recursive] [--depth N]
  mudctl get <remote_path> [local_path] [--recursive]
  mudctl put <local_path> <remote_path> [--dry-run] [--yes] [--expect N] [--recursive]
  mudctl diff <local_path> <remote_path>
  mudctl search <patron> [ruta] [--regex] [--case-insensitive]
  mudctl grep <patron> [ruta] [--regex] [--case-insensitive] [--max N] [--all]
  mudctl mkdir <ruta> [--parents] [--dry-run] [--yes]
  mudctl rm <ruta> [--recursive] [--dry-run] [--yes] [--expect N] [--max N]
  mudctl cat <ruta>
  mudctl info <ruta>
  mudctl tail <ruta> [--lines N]
  mudctl move <origen> <destino> [--dry-run] [--yes]
  mudctl cp <origen> <destino> [--dry-run] [--yes]
  mudctl scaffold <ejemplo> <destino-nuevo> [--dry-run] [--yes]
  mudctl status <carpeta-local> <ruta-remota> [--all]
  mudctl apply <parche> <ruta-remota> [--dry-run] [--yes]
  mudctl plan <plan.json> [--dry-run] [--yes]
  mudctl sync <pull|push|status> <args> [--dry-run] [--yes] [--expect N] [--parallel N] [--prune]
  mudctl watch <ruta> [--snapshot archivo]
  mudctl describe

Salida: texto plano por defecto (NVDA), --json para agentes.
Codigos de salida: 0=OK, 2=uso, 3=auth, 4=red, 5=no encontrado, 6=abortado.
"""