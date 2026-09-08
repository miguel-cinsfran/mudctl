from __future__ import annotations

import json
import os
import pytest

from tests.test_v02 import FakeFTP, make_backend


def make_backend_v03():
    b = make_backend()
    b._ftp.files["/otros/notas.txt"] = "notas varias\n".encode()
    b._ftp.files["/hazrakh/log.txt"] = "\n".join(f"linea {i}" for i in range(1, 51)).encode()
    b._ftp.dirs.add("/hazrakh/pack")
    return b


def test_grep_lpc_filter_and_all():
    b = make_backend_v03()
    r = b.grep("notas", "/otros")
    assert r["status"] == "ok"
    assert r["hits"] == []
    r2 = b.grep("notas", "/otros", all_files=True)
    assert len(r2["hits"]) == 1


def test_status_hash_states(tmp_path):
    b = make_backend_v03()
    local = tmp_path / "mago"
    local.mkdir()
    (local / "espada.c").write_bytes(b._ftp.files["/otros/mago/espada.c"])
    (local / "escudo.c").write_text("contenido distinto")
    (local / "mia.c").write_text("solo local")
    r = b.status(str(local), "/otros/mago")
    assert r["status"] == "ok"
    assert r["same"] == ["espada.c"]
    assert r["changed"] == ["escudo.c"]
    assert r["only_local"] == ["mia.c"]
    assert r["only_remote"] == []


def test_tail_exact():
    b = make_backend_v03()
    r = b.tail("/hazrakh/log.txt", lines=5)
    assert r["status"] == "ok"
    assert r["lines"] == ["linea 46", "linea 47", "linea 48", "linea 49", "linea 50"]
    assert r["total"] == 50


def test_watch_detects_new(tmp_path):
    b = make_backend_v03()
    snap = str(tmp_path / "snap.json")
    r1 = b.watch("/otros/mago", snapshot_file=snap)
    assert r1["status"] == "ok"
    assert r1["new"] == sorted(r1["new"]) and len(r1["new"]) == 2
    b._ftp.files["/otros/mago/nuevo.c"] = "nuevo\n".encode()
    r2 = b.watch("/otros/mago", snapshot_file=snap)
    assert r2["new"] == ["/otros/mago/nuevo.c"]
    assert r2["gone"] == []


def test_apply_dry_real_and_broken(tmp_path):
    b = make_backend_v03()
    b._ftp.files["/hazrakh/espada.c"] = b._ftp.files["/otros/mago/espada.c"]
    patch = tmp_path / "fix.patch"
    patch.write_text("--- a/espada.c\n+++ b/espada.c\n@@ -1,2 +1,2 @@\n-hereda de arma\n+hereda de arma magica\n objeto espada\n")
    r = b.apply(str(patch), "/hazrakh/espada.c", dry_run=True)
    assert r["status"] == "ok" and r["hunks"] == 1
    r2 = b.apply(str(patch), "/hazrakh/espada.c", dry_run=False)
    assert r2["status"] == "ok"
    assert b"magica" in b._ftp.files["/hazrakh/espada.c"]
    bad = tmp_path / "bad.patch"
    bad.write_text("--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n-esta linea no existe\n+otra\n")
    r3 = b.apply(str(bad), "/hazrakh/espada.c", dry_run=False)
    assert r3["code"] == "ABORTED"


def test_plan_dry_apply_and_stop(tmp_path):
    b = make_backend_v03()
    src = tmp_path / "a.c"
    src.write_text("hola")
    ops = [
        {"verb": "mkdir", "path": "/hazrakh/pack"},
        {"verb": "put", "local": str(src), "remote": "/hazrakh/pack/a.c"},
        {"verb": "cp", "source": "/otros/mago/escudo.c", "destination": "/hazrakh/pack/escudo.c"},
    ]
    r = b.plan(ops, dry_run=True)
    assert r["status"] == "ok" and len(r["steps"]) == 3
    r2 = b.plan(ops, dry_run=False)
    assert r2["status"] == "ok" and len(r2["done"]) == 3
    assert "/hazrakh/pack/a.c" in b._ftp.files
    bad_ops = [
        {"verb": "mkdir", "path": "/hazrakh/ok"},
        {"verb": "cp", "source": "/otros/mago/espada.c", "destination": "/otros/robado.c"},
    ]
    r3 = b.plan(bad_ops, dry_run=True)
    assert r3["code"] == "ABORTED"


def test_cli_v03_exits(tmp_path):
    from mudctl.commands import run
    b = make_backend_v03()
    local = tmp_path / "mago"
    local.mkdir()
    assert run(b, ["status", str(local), "/otros/mago"]) == 0
    assert run(b, ["tail", "/hazrakh/log.txt", "--lines", "3"]) == 0
    assert run(b, ["watch", "/otros/mago", "--snapshot", str(tmp_path / "s.json")]) == 0
    assert run(b, ["apply"]) == 2
    assert run(b, ["plan"]) == 2


def test_rm_guard_dry_and_real():
    b = make_backend_v03()
    r = b.rm("/otros/mago/espada.c", dry_run=True, expect=1)
    assert r["code"] == "ABORTED"
    assert "/otros/mago/espada.c" in b._ftp.files
    r2 = b.rm("/otros/mago/espada.c", dry_run=False, expect=1)
    assert r2["code"] == "ABORTED"
    assert "/otros/mago/espada.c" in b._ftp.files
    r3 = b.rm("/hazrakh/log.txt", dry_run=False, expect=1)
    assert r3["status"] == "ok"
    assert "/hazrakh/log.txt" not in b._ftp.files


def test_rm_recursive_real():
    b = make_backend_v03()
    b._ftp.dirs.add("/hazrakh/borrame")
    b._ftp.dirs.add("/hazrakh/borrame/sub")
    b._ftp.files["/hazrakh/borrame/a.c"] = b"a"
    b._ftp.files["/hazrakh/borrame/sub/b.c"] = b"b"
    r = b.rm("/hazrakh/borrame", recursive=True, dry_run=True)
    assert r["status"] == "ok" and r["files"] == 2
    assert "/hazrakh/borrame/a.c" in b._ftp.files
    r2 = b.rm("/hazrakh/borrame", recursive=True, dry_run=False, expect=2)
    assert r2["status"] == "ok" and r2["files"] == 2
    assert "/hazrakh/borrame/a.c" not in b._ftp.files
    assert "/hazrakh/borrame/sub/b.c" not in b._ftp.files
    r3 = b.rm("/otros/mago", recursive=True, dry_run=False)
    assert r3["code"] == "ABORTED"


def test_mkdir_move_dry():
    b = make_backend_v03()
    r = b.mkdir("/hazrakh/nueva")
    assert r["status"] == "ok" and r["action"] == "dry-run"
    assert "/hazrakh/nueva" not in b._ftp.dirs
    r2 = b.mkdir("/hazrakh/nueva", dry_run=False)
    assert r2["status"] == "ok"
    r3 = b.move("/hazrakh/log.txt", "/hazrakh/log2.txt")
    assert r3["status"] == "ok" and r3["action"] == "dry-run"
    assert "/hazrakh/log2.txt" not in b._ftp.files
