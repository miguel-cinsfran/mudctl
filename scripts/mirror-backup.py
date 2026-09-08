#!/usr/bin/env python3
"""mirror-backup.py — Backup del home FTP con rotación de 3 días.

Usa mudctl get --recursive para bajar el home del servidor y guarda una
copia con marca de fecha. Los backups más viejos de 3 días se borran.
Sin LLM, sin magia: solo Python estándar + subprocess.

Uso:
    python scripts/mirror-backup.py              # backup normal
    python scripts/mirror-backup.py --dry-run      # listaría qué haría
    python scripts/mirror-backup.py --keep N       # guardar N días en vez de 3
"""

import argparse
import datetime
import os
import subprocess
import shutil
import sys
from pathlib import Path

# Configuración
SCRIPT_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = SCRIPT_DIR
BACKUP_ROOT = Path(os.environ.get("MUD_BACKUP_ROOT", str(REPO_DIR / "backups")))
DAYS_TO_KEEP = 3
MUDCTL = str(Path(os.environ.get("MUDCTL", str(REPO_DIR / ".venv" / "Scripts" / "python.exe"))))
MUDCTL_MODULE = "mudctl"  # módulo a ejecutar con uv

# Ruta al script que levanta el entorno del repo
ENV_SCRIPT = REPO_DIR / "scripts" / "env_helper.py"


def run_mudctl(args: list[str], timeout: int = 300) -> tuple[int, str, str]:
    """Ejecuta mudctl y retorna (exit_code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "mudctl"] + args
    # Agregar el directorio del repo al PYTHONPATH para que encuentre el módulo
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_DIR),
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout excedido"
    except Exception as e:
        return -1, "", str(e)


def get_mirror_date() -> str:
    """Fecha actual en formato YYYY-MM-DD."""
    return datetime.date.today().isoformat()


def create_backup(mirror_path: Path, date_str: str, dry_run: bool = False) -> bool:
    """Crea un backup del espejo local en un directorio con marca de fecha."""
    date_dir = BACKUP_ROOT / date_str
    if date_dir.exists():
        print(f"[INFO] El directorio {date_dir} ya existe, reutilizando.")
        return True

    if dry_run:
        print(f"[DRY-RUN] Crearía: {date_dir}")
        return True

    try:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        # Copiar todo el contenido del espejo
        shutil.copytree(mirror_path, date_dir)
        print(f"[OK] Backup creado: {date_dir}")
        return True
    except Exception as e:
        print(f"[ERROR] Fallo al crear backup: {e}")
        return False


def cleanup_old_backups(days: int, dry_run: bool = False) -> int:
    """Borra backups más viejos de N días. Retorna cantidad borrada."""
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    borrados = 0

    if not BACKUP_ROOT.exists():
        return 0

    for entry in BACKUP_ROOT.iterdir():
        if not entry.is_dir():
            continue
        try:
            entry_date = datetime.date.fromisoformat(entry.name)
            if entry_date < cutoff:
                if dry_run:
                    print(f"[DRY-RUN] Borraría: {entry}")
                else:
                    shutil.rmtree(entry)
                    print(f"[OK] Borrado: {entry}")
                borrados += 1
        except ValueError:
            # Nombre no es fecha, ignorar
            continue

    return borrados


def main():
    parser = argparse.ArgumentParser(
        description="Backup del home FTP con rotación de 3 días"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Lista las operaciones sin ejecutar nada"
    )
    parser.add_argument(
        "--keep", type=int, default=DAYS_TO_KEEP,
        help=f"Días a conservar (default: {DAYS_TO_KEEP})"
    )
    parser.add_argument(
        "--mirror", type=str, default=None,
        help="Ruta al espejo local (default: C:/Users/ic_ma/AppData/Local/Temp/mudctl-bateria2)"
    )
    args = parser.parse_args()

    mirror_path = Path(args.mirror) if args.mirror else Path(
        "C:/Users/ic_ma/AppData/Local/Temp/mudctl-bateria2"
    )
    date_str = get_mirror_date()

    print(f"=== mirror-backup {date_str} ===")
    print(f"Espejo: {mirror_path}")
    print(f"Backup root: {BACKUP_ROOT}")
    print(f"Retention: {args.keep} días")
    print()

    # Paso 1: Crear backup del espejo actual
    if not create_backup(mirror_path, date_str, args.dry_run):
        print("[FATAL] No se pudo crear el backup. Abortando.")
        sys.exit(1)

    # Paso 2: Limpiar backups viejos
    borrados = cleanup_old_backups(args.keep, args.dry_run)
    print()
    print(f"[RESUMEN] Backup {date_str} creado, {borrados} backups viejos borrados.")
    print("[DONE]")


if __name__ == "__main__":
    main()
