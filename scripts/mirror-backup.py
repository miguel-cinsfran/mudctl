#!/usr/bin/env python3
"""Backup fresco del home FTP con rotación corta y verificación.

Objetivo: conservar tres días de protección local contra cambios accidentales.
No depende de un LLM ni de un espejo previo:
1. descarga el home remoto a staging;
2. exige que la descarga produzca archivos;
3. escribe un manifiesto con tamaño y SHA-256;
4. mueve staging a una carpeta fechada;
5. rota únicamente backups antiguos.

Si falla la descarga, el hash, el espacio o el lock, no borra backups existentes.

Uso:
    python scripts/mirror-backup.py
    python scripts/mirror-backup.py --dry-run
    python scripts/mirror-backup.py --verify backups/2026-09-08
    python scripts/mirror-backup.py --keep 3
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
BACKUP_ROOT = Path(os.environ.get("MUD_BACKUP_ROOT", str(REPO_DIR / "backups")))
REMOTE_HOME = os.environ.get("MUD_BACKUP_REMOTE", "/w/hazrakh")
DAYS_TO_KEEP = 3
LOCK_PATH = BACKUP_ROOT / ".mirror-backup.lock"
MANIFEST_NAME = ".mudctl-backup.json"
STALE_LOCK_SECONDS = 6 * 60 * 60
MIN_FREE_BYTES = 50 * 1024 * 1024


def python_runner() -> str:
    candidates = [
        REPO_DIR / ".venv" / "Scripts" / "python.exe",
        REPO_DIR / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _lock_is_stale() -> bool:
    try:
        stat = LOCK_PATH.stat()
        age = time.time() - stat.st_mtime
        content = LOCK_PATH.read_text(encoding="utf-8", errors="replace")
        pid = int(content.partition("=")[2].strip())
        if pid > 0:
            try:
                os.kill(pid, 0)
                return False
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
        return age > STALE_LOCK_SECONDS
    except (OSError, ValueError):
        try:
            return time.time() - LOCK_PATH.stat().st_mtime > STALE_LOCK_SECONDS
        except OSError:
            return False


def acquire_lock() -> bool:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists() and _lock_is_stale():
        print("[WARN] Lock antiguo recuperado.")
        LOCK_PATH.unlink(missing_ok=True)
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\n")
        return True
    except FileExistsError:
        return False


def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def run_mudctl(destination: Path, timeout: int = 900) -> tuple[int, str, str]:
    command = [
        python_runner(), "-m", "mudctl", "get", REMOTE_HOME,
        str(destination), "--recursive",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            command, cwd=str(REPO_DIR), env=env,
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout de descarga excedido"
    except OSError as exc:
        return 127, "", f"no se pudo ejecutar mudctl: {type(exc).__name__}"


def file_entries(root: Path) -> list[Path]:
    return sorted(item for item in root.rglob("*") if item.is_file())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict:
    files = []
    for path in file_entries(root):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_NAME:
            continue
        files.append({
            "path": relative,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "format": 1,
        "remote": REMOTE_HOME,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": files,
    }


def write_manifest(root: Path, manifest: dict) -> None:
    target = root / MANIFEST_NAME
    temporary = root / f"{MANIFEST_NAME}.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def verify_backup(root: Path) -> int:
    manifest_path = root / MANIFEST_NAME
    if not root.is_dir() or not manifest_path.is_file():
        print(f"[ERROR] Falta el backup o su manifiesto: {root}")
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {item["path"]: item for item in manifest["files"]}
    except (OSError, ValueError, KeyError, TypeError):
        print("[ERROR] Manifiesto inválido.")
        return 1

    actual = {}
    errors = []
    for path in file_entries(root):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_NAME:
            continue
        actual[relative] = path
    for relative, item in expected.items():
        path = actual.get(relative)
        if path is None:
            errors.append(f"falta: {relative}")
            continue
        if path.stat().st_size != item["size"]:
            errors.append(f"tamaño: {relative}")
            continue
        if sha256_file(path) != item["sha256"]:
            errors.append(f"hash: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"extra: {relative}")

    if errors:
        print(f"[ERROR] Verificación fallida: {len(errors)} diferencias")
        for error in errors[:10]:
            print(f"  - {error}")
        return 1
    print(f"[OK] Backup íntegro: {len(expected)} archivos verificados")
    return 0


def dated_destination(date_str: str) -> Path:
    candidate = BACKUP_ROOT / date_str
    suffix = 2
    while candidate.exists():
        candidate = BACKUP_ROOT / f"{date_str}-{suffix}"
        suffix += 1
    return candidate


def rotate_backups(keep: int, today: datetime.date, dry_run: bool) -> int:
    cutoff = today - datetime.timedelta(days=keep)
    removed = 0
    if not BACKUP_ROOT.exists():
        return removed
    for entry in BACKUP_ROOT.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            entry_date = datetime.date.fromisoformat(entry.name[:10])
        except ValueError:
            continue
        if entry_date < cutoff:
            if dry_run:
                print(f"[DRY-RUN] Borraría: {entry}")
            else:
                shutil.rmtree(entry)
                print(f"[OK] Borrado: {entry}")
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup fresco del home FTP")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep", type=int, default=DAYS_TO_KEEP)
    parser.add_argument("--verify", metavar="BACKUP", help="verifica un backup existente")
    args = parser.parse_args()

    if args.verify:
        return verify_backup(Path(args.verify))
    if args.keep < 1:
        print("[ERROR] --keep debe ser al menos 1 día")
        return 2

    today = datetime.date.today()
    date_text = today.isoformat()
    print(f"=== mirror-backup {date_text} ===")
    print(f"Remoto: {REMOTE_HOME}")
    print(f"Destino: {BACKUP_ROOT}")
    print(f"Retención: {args.keep} días")

    if args.dry_run:
        print(f"[DRY-RUN] Descargaría un staging fresco y crearía {BACKUP_ROOT / date_text}")
        rotate_backups(args.keep, today, dry_run=True)
        return 0

    if not acquire_lock():
        print(f"[ERROR] Ya hay otro backup en ejecución: {LOCK_PATH}")
        return 6

    staging: Path | None = None
    try:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(BACKUP_ROOT).free
        if free < MIN_FREE_BYTES:
            print(f"[ERROR] Espacio libre insuficiente: {free} bytes")
            return 1
        staging = Path(tempfile.mkdtemp(prefix=".mirror-staging-", dir=str(BACKUP_ROOT)))
        print("[INFO] Descargando a staging nuevo...")
        code, _stdout, stderr = run_mudctl(staging)
        files = file_entries(staging)
        if code != 0 or not files:
            detail = stderr.strip() or f"mudctl terminó con código {code}"
            print(f"[ERROR] Descarga incompleta: {detail}")
            print("[INFO] No se modificaron ni rotaron backups existentes.")
            return 1

        manifest = build_manifest(staging)
        write_manifest(staging, manifest)
        destination = dated_destination(date_text)
        staging.rename(destination)
        staging = None
        print(f"[OK] Backup creado: {destination}")
        print(f"[OK] Archivos descargados: {len(manifest['files'])}")
        if verify_backup(destination) != 0:
            print("[ERROR] El backup recién creado no pasó la verificación.")
            return 1
        removed = rotate_backups(args.keep, today, dry_run=False)
        print(f"[RESUMEN] Backup válido; {removed} backups viejos borrados.")
        return 0
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
