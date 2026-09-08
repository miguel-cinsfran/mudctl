#!/usr/bin/env python3
"""Backup fresco del home FTP con rotación de N días.

El script no depende de un LLM ni de un espejo previo:
1. descarga el home remoto a un staging nuevo;
2. exige que la descarga produzca archivos;
3. mueve el staging a una carpeta fechada;
4. borra únicamente backups fechados más viejos de N días.

Si falla la descarga, no borra backups existentes.

Uso:
    python scripts/mirror-backup.py
    python scripts/mirror-backup.py --dry-run
    python scripts/mirror-backup.py --keep 3
"""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
BACKUP_ROOT = Path(os.environ.get("MUD_BACKUP_ROOT", str(REPO_DIR / "backups")))
REMOTE_HOME = os.environ.get("MUD_BACKUP_REMOTE", "/w/hazrakh")
DAYS_TO_KEEP = 3
LOCK_PATH = BACKUP_ROOT / ".mirror-backup.lock"


def python_runner() -> str:
    """Devuelve el Python del entorno del repo cuando existe."""
    candidates = [
        REPO_DIR / ".venv" / "Scripts" / "python.exe",
        REPO_DIR / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def acquire_lock() -> bool:
    """Adquiere un lock sin esperar; evita dos backups simultáneos."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
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
    """Descarga el home remoto al destino y devuelve código/salidas."""
    command = [
        python_runner(), "-m", "mudctl", "get", REMOTE_HOME,
        str(destination), "--recursive",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            command,
            cwd=str(REPO_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout de descarga excedido"
    except OSError as exc:
        return 127, "", f"no se pudo ejecutar mudctl: {type(exc).__name__}"


def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def dated_destination(date_str: str) -> Path:
    """Busca una carpeta fechada libre sin sobrescribir un backup."""
    candidate = BACKUP_ROOT / date_str
    suffix = 2
    while candidate.exists():
        candidate = BACKUP_ROOT / f"{date_str}-{suffix}"
        suffix += 1
    return candidate


def rotate_backups(keep: int, today: datetime.date, dry_run: bool) -> int:
    """Elimina solo carpetas fechadas que superen la retención."""
    cutoff = today - datetime.timedelta(days=keep)
    removed = 0
    if not BACKUP_ROOT.exists():
        return removed

    for entry in BACKUP_ROOT.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        date_text = entry.name[:10]
        try:
            entry_date = datetime.date.fromisoformat(date_text)
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
    args = parser.parse_args()

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
        staging = Path(tempfile.mkdtemp(prefix=".mirror-staging-", dir=str(BACKUP_ROOT)))
        print(f"[INFO] Descargando a staging nuevo...")
        code, _stdout, stderr = run_mudctl(staging)
        files = count_files(staging)
        if code != 0 or files == 0:
            detail = stderr.strip() or f"mudctl terminó con código {code}"
            print(f"[ERROR] Descarga incompleta: {detail}")
            print("[INFO] No se modificaron ni rotaron backups existentes.")
            return 1

        destination = dated_destination(date_text)
        staging.rename(destination)
        staging = None
        print(f"[OK] Backup creado: {destination}")
        print(f"[OK] Archivos descargados: {files}")

        removed = rotate_backups(args.keep, today, dry_run=False)
        print(f"[RESUMEN] Backup válido; {removed} backups viejos borrados.")
        return 0
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
