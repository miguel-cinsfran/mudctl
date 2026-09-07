from __future__ import annotations

import io
import os
import pytest


class FakeFTP:
    def __init__(self):
        self.dirs = {"/", "/otros", "/otros/mago", "/hazrakh"}
        self.files = {
            "/otros/mago/espada.c": "hereda de arma\nobjeto espada\n".encode(),
            "/otros/mago/escudo.c": "hereda de armadura\nobjeto escudo\n".encode(),
        }
        self._pwd = "/"

    def pwd(self):
        return self._pwd

    def cwd(self, path):
        if path in self.dirs:
            self._pwd = path
            return
        raise Exception("550 no es directorio")

    def mlsd(self, path):
        if path not in self.dirs:
            raise Exception("550 no existe")
        for d in sorted(self.dirs):
            if d != path and d.startswith(path.rstrip("/") + "/") and "/" not in d[len(path.rstrip("/") + "/"):]:
                yield (d.split("/")[-1], {"type": "dir"})
        for f, _ in sorted(self.files.items()):
            parent = "/" + "/".join(f.strip("/").split("/")[:-1])
            parent = parent if parent != "/" else "/"
            if parent == path:
                yield (f.split("/")[-1], {"type": "file"})

    def nlst(self, path):
        return [n for n, _f in self.mlsd(path)]

    def mkd(self, path):
        self.dirs.add(path)

    def retrbinary(self, cmd, cb):
        path = cmd.split(" ", 1)[1]
        if path not in self.files:
            raise Exception("550 no existe")
        cb(self.files[path])

    def storbinary(self, cmd, fp):
        path = cmd.split(" ", 1)[1]
        parent = "/" + "/".join(path.strip("/").split("/")[:-1])
        if parent == "/":
            pass
        elif parent not in self.dirs:
            raise Exception("550 carpeta no existe")
        self.files[path] = fp.read()

    def rename(self, src, dst):
        if src in self.files:
            self.files[dst] = self.files.pop(src)
            return
        raise Exception("550 no existe")

    def size(self, path):
        if path in self.files:
            return len(self.files[path])
        raise Exception("550 no existe")

    def delete(self, path):
        del self.files[path]

    def rmd(self, path):
        self.dirs.remove(path)


def make_backend():
    os.environ["MUD_USER"] = "hazrakh"
    os.environ["MUD_HOME"] = "/hazrakh"
    from mudctl.backend import FTPClientBackend
    b = FTPClientBackend()
    b._ftp = FakeFTP()
    return b


def test_guard_blocks_write_outside_home():
    b = make_backend()
    assert b.put("x", "/otros/mago/mio.c", dry_run=True)["code"] == "ABORTED"
    assert b.cp("/otros/mago/espada.c", "/otros/mago/copia.c", dry_run=True)["code"] == "ABORTED"
    assert b.mkdir("/otros/mago/nuevo")["code"] == "ABORTED"
    assert b.move("/hazrakh/a.c", "/otros/mago/a.c")["code"] == "ABORTED"
    assert b.scaffold("/otros/mago", "/otros/mago/copia")["code"] == "ABORTED"


def test_get_recursive(tmp_path):
    b = make_backend()
    dest = str(tmp_path / "mago")
    r = b.get("/otros/mago", dest, recursive=True)
    assert r["status"] == "ok"
    assert r["files"] == 2
    assert (tmp_path / "mago" / "espada.c").exists()


def test_put_recursive_dry_then_real(tmp_path):
    b = make_backend()
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.c").write_text("a")
    (src / "sub" / "b.c").write_text("b")
    r = b.put(str(src), "/hazrakh/propio", dry_run=True, recursive=True)
    assert r["status"] == "ok"
    assert r["files"] == 2
    assert "/hazrakh/propio/a.c" not in b._ftp.files
    r2 = b.put(str(src), "/hazrakh/propio", dry_run=False, recursive=True)
    assert r2["status"] == "ok"
    assert r2["files"] == 2


def test_cp_and_scaffold():
    b = make_backend()
    r = b.cp("/otros/mago/espada.c", "/hazrakh/espada.c", dry_run=False)
    assert r["status"] == "ok"
    assert b._ftp.files["/hazrakh/espada.c"] == b._ftp.files["/otros/mago/espada.c"]
    r2 = b.scaffold("/otros/mago/espada.c", "/hazrakh/espada.c", dry_run=False)
    assert r2["code"] == "ABORTED"
    r3 = b.scaffold("/otros/mago", "/hazrakh/mago", dry_run=False)
    assert r3["status"] == "ok"
    assert r3["files"] == 2


def test_grep_finds_content():
    b = make_backend()
    r = b.grep("espada", "/otros", case_insensitive=True)
    assert r["status"] == "ok"
    assert r["scanned"] == 2
    assert any(h["path"].endswith("espada.c") for h in r["hits"])


def test_cli_cp_dry_exit_zero():
    from mudctl.commands import run
    b = make_backend()
    assert run(b, ["cp", "/otros/mago/espada.c", "/hazrakh/e.c", "--dry-run"]) == 0
    assert run(b, ["cp", "/otros/mago/espada.c", "/otros/copia.c"]) == 6
    assert run(b, ["grep", "espada", "/otros"]) == 0
