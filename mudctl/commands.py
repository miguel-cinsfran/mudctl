from __future__ import annotations

import sys
from typing import Callable

from mudctl.backend import FTPClientBackend, FTPBackend
from mudctl.errors import AuthenticationError, NetworkError
from mudctl.output import Result, OutputFormatter, ExitCode, make_result, make_error


def run(backend: FTPBackend, argv: list[str] | None = None) -> int:
    from mudctl.output import OutputFormat
    args = argv if argv is not None else sys.argv[1:]
    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]
    if not args:
        print(backend.describe())
        return ExitCode.OK.value

    verb = args[0].lower()
    rest = args[1:]

    # Mostrar help si se pide o si no hay verbo conocido
    if "--help" in args or verb == "-h":
        print(FTPClientBackend().describe())
        return ExitCode.OK.value

    dispatcher: dict[str, Callable] = {
        "doctor": lambda: handle_doctor(backend),
        "list": lambda: handle_list(backend, rest),
        "get": lambda: handle_get(backend, rest),
        "put": lambda: handle_put(backend, rest),
        "diff": lambda: handle_diff(backend, rest),
        "search": lambda: handle_search(backend, rest),
        "mkdir": lambda: handle_mkdir(backend, rest),
        "rm": lambda: handle_rm(backend, rest),
        "cat": lambda: handle_cat(backend, rest),
        "info": lambda: handle_info(backend, rest),
        "move": lambda: handle_move(backend, rest),
        "cp": lambda: handle_cp(backend, rest),
        "grep": lambda: handle_grep(backend, rest),
        "scaffold": lambda: handle_scaffold(backend, rest),
        "status": lambda: handle_status(backend, rest),
        "tail": lambda: handle_tail(backend, rest),
        "watch": lambda: handle_watch(backend, rest),
        "apply": lambda: handle_apply(backend, rest),
        "plan": lambda: handle_plan(backend, rest),
        "describe": lambda: make_result(True, "describe", data={"help": backend.describe()}),
    }

    if verb not in dispatcher:
        print(f"Error: unknown verb '{verb}'. Run 'mudctl describe' for help.")
        return ExitCode.USAGE.value

    handler = dispatcher[verb]
    result = handler()

    if isinstance(result, dict) and "status" in result:
        from mudctl.output import make_result as _mr
        is_ok = result.get("status") == "ok"
        result = _mr(is_ok, verb, data=result)
    elif isinstance(result, str):
        result = make_result(True, verb, data={"output": result})

    if json_mode and isinstance(result, Result):
        from mudctl.output import OutputFormat as _Fmt
        result.format = _Fmt.JSON
    print(OutputFormatter.format(result))
    return OutputFormatter.exit_code(result)


def handle_doctor(backend: FTPBackend) -> Result:
    data = backend.doctor()
    if data.get("status") == "ok":
        return make_result(True, "doctor", data=data)
    return make_result(False, "doctor", error=data)


def handle_list(backend: FTPBackend, args: list[str]) -> Result:
    path = args[0] if args and not args[0].startswith("--") else "/"
    recursive = "--recursive" in args
    depth = None
    for i, a in enumerate(args):
        if a == "--depth" and i + 1 < len(args):
            try:
                depth = int(args[i + 1])
            except ValueError:
                return make_result(False, "list", error={"code": "USAGE", "message": "Depth debe ser numero", "hint": "Usa --depth N con N entero"})
    data = backend.list(path, recursive=recursive, depth=depth)
    return make_result(True, "list", data=data)


def handle_get(backend: FTPBackend, args: list[str]) -> Result:
    if not args or args[0].startswith("--"):
        return make_result(False, "get", error={"code": "USAGE", "message": "Usage: mudctl get <remote_path> [local_path] [--recursive]", "hint": "Provide at least the remote path."})
    remote_path = args[0]
    local_path = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    recursive = "--recursive" in args
    data = backend.get(remote_path, local_path, recursive=recursive)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "get", data=data)
    return make_result(False, "get", error=data)


def handle_put(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "put", error={"code": "USAGE", "message": "Usage: mudctl put <local_path> <remote_path> [--dry-run] [--yes] [--expect N]", "hint": "Provide local and remote paths."})
    local_path = args[0]
    remote_path = args[1]
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    recursive = "--recursive" in args
    yes = "--yes" in args
    expect = None
    for i, a in enumerate(args):
        if a == "--expect" and i + 1 < len(args):
            try:
                expect = int(args[i + 1])
            except ValueError:
                return make_result(False, "put", error={"code": "USAGE", "message": "Expect debe ser numero", "hint": "Usa --expect N con N entero"})
    if expect is not None and not recursive and expect != 1:
        return make_result(False, "put", error={"code": "ABORTED", "message": f"Expect {expect} no coincide con 1", "hint": "Revisa --expect"})
    data = backend.put(local_path, remote_path, dry_run=dry_run, recursive=recursive, expect=expect)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "put", data=data)
    return make_result(False, "put", error=data)


def handle_diff(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "diff", error={"code": "USAGE", "message": "Usage: mudctl diff <local_path> <remote_path>", "hint": "Provide local and remote paths."})
    local_path = args[0]
    remote_path = args[1]
    data = backend.diff(local_path, remote_path)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "diff", data=data)
    return make_result(False, "diff", error=data)


def handle_search(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "search", error={"code": "USAGE", "message": "Usage: mudctl search <pattern> [path] [--regex] [--case-insensitive]", "hint": "Provide at least the search pattern."})
    pattern = args[0]
    path = args[1] if len(args) > 1 else "/"
    regex = "--regex" in args
    case_insensitive = "--case-insensitive" in args
    data = backend.search(pattern, path, regex=regex, case_insensitive=case_insensitive)
    return make_result(True, "search", data=data)


def handle_mkdir(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "mkdir", error={"code": "USAGE", "message": "Usage: mudctl mkdir <path> [--parents] [--dry-run] [--yes]", "hint": "Provide at least the path."})
    path = args[0]
    parents = "--parents" in args
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.mkdir(path, parents=parents, dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "mkdir", data=data)
    return make_result(False, "mkdir", error=data)


def handle_rm(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "rm", error={"code": "USAGE", "message": "Usage: mudctl rm <path> [--recursive] [--dry-run] [--yes] [--expect N] [--max N]", "hint": "Provide at least the path."})
    path = args[0]
    recursive = "--recursive" in args
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    yes = "--yes" in args
    expect = None
    max_files = None
    for i, a in enumerate(args):
        if a == "--expect" and i + 1 < len(args):
            try:
                expect = int(args[i + 1])
            except ValueError:
                return make_result(False, "rm", error={"code": "USAGE", "message": "Expect debe ser numero", "hint": "Usa --expect N con N entero"})
        if a == "--max" and i + 1 < len(args):
            try:
                max_files = int(args[i + 1])
            except ValueError:
                return make_result(False, "rm", error={"code": "USAGE", "message": "Max debe ser numero", "hint": "Usa --max N con N entero"})
    data = backend.rm(path, recursive=recursive, dry_run=dry_run, expect=expect, max_files=max_files)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "rm", data=data)
    return make_result(False, "rm", error=data)


def handle_cat(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "cat", error={"code": "USAGE", "message": "Usage: mudctl cat <path>", "hint": "Provide at least the path."})
    path = args[0]
    data = backend.cat(path)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "cat", data=data)
    return make_result(False, "cat", error=data)


def handle_info(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "info", error={"code": "USAGE", "message": "Usage: mudctl info <path>", "hint": "Provide at least the path."})
    path = args[0]
    data = backend.info(path)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "info", data=data)
    return make_result(False, "info", error=data)


def handle_move(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "move", error={"code": "USAGE", "message": "Usage: mudctl move <source> <destination> [--dry-run] [--yes]", "hint": "Provide source and destination."})
    source = args[0]
    destination = args[1]
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.move(source, destination, dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "move", data=data)
    return make_result(False, "move", error=data)


def handle_cp(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "cp", error={"code": "USAGE", "message": "Usage: mudctl cp <source> <destination> [--dry-run] [--yes]", "hint": "Copia dentro del servidor, el destino debe estar en tu carpeta."})
    source = args[0]
    destination = args[1]
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.cp(source, destination, dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "cp", data=data)
    return make_result(False, "cp", error=data)


def handle_grep(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "grep", error={"code": "USAGE", "message": "Usage: mudctl grep <pattern> [path] [--regex] [--case-insensitive] [--max N]", "hint": "Provide at least the search pattern."})
    pattern = args[0]
    path = args[1] if len(args) > 1 and not args[1].startswith("--") else "/"
    regex = "--regex" in args
    case_insensitive = "--case-insensitive" in args
    all_files = "--all" in args
    max_hits = 50
    for i, a in enumerate(args):
        if a == "--max" and i + 1 < len(args):
            try:
                max_hits = int(args[i + 1])
            except ValueError:
                return make_result(False, "grep", error={"code": "USAGE", "message": "Max debe ser numero", "hint": "Usa --max N con N entero"})
    data = backend.grep(pattern, path, regex=regex, case_insensitive=case_insensitive, max_hits=max_hits, all_files=all_files)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "grep", data=data)
    return make_result(False, "grep", error=data)


def handle_scaffold(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "scaffold", error={"code": "USAGE", "message": "Usage: mudctl scaffold <ejemplo> <destino-nuevo> [--dry-run] [--yes]", "hint": "Copia un ejemplo ajeno a una ruta nueva tuya sin pisar nada."})
    source = args[0]
    destination = args[1]
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.scaffold(source, destination, dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "scaffold", data=data)
    return make_result(False, "scaffold", error=data)


def handle_status(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "status", error={"code": "USAGE", "message": "Usage: mudctl status <carpeta-local> <ruta-remota> [--all]", "hint": "Compara tu carpeta local contra la remota por hash."})
    data = backend.status(args[0], args[1], all_files=("--all" in args))
    if "status" in data and data["status"] == "ok":
        return make_result(True, "status", data=data)
    return make_result(False, "status", error=data)


def handle_tail(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "tail", error={"code": "USAGE", "message": "Usage: mudctl tail <ruta> [--lines N]", "hint": "Muestra la cola de un fichero remoto."})
    lines = 30
    for i, a in enumerate(args):
        if a == "--lines" and i + 1 < len(args):
            try:
                lines = int(args[i + 1])
            except ValueError:
                return make_result(False, "tail", error={"code": "USAGE", "message": "Lines debe ser numero", "hint": "Usa --lines N con N entero"})
    data = backend.tail(args[0], lines=lines)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "tail", data=data)
    return make_result(False, "tail", error=data)


def handle_watch(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "watch", error={"code": "USAGE", "message": "Usage: mudctl watch <ruta> [--snapshot archivo]", "hint": "Lista novedades contra la corrida anterior."})
    snap = None
    for i, a in enumerate(args):
        if a == "--snapshot" and i + 1 < len(args):
            snap = args[i + 1]
    data = backend.watch(args[0], snapshot_file=snap)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "watch", data=data)
    return make_result(False, "watch", error=data)


def handle_apply(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "apply", error={"code": "USAGE", "message": "Usage: mudctl apply <parche> <ruta-remota> [--dry-run] [--yes]", "hint": "Aplica un parche unificado a un fichero remoto."})
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.apply(args[0], args[1], dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "apply", data=data)
    return make_result(False, "apply", error=data)


def handle_plan(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "plan", error={"code": "USAGE", "message": "Usage: mudctl plan <plan.json> [--dry-run] [--yes]", "hint": "Valida y aplica un lote de operaciones con un solo --yes."})
    import json
    try:
        ops = json.loads(open(args[0], encoding="utf-8").read())
    except Exception as e:
        return make_result(False, "plan", error={"code": "USAGE", "message": f"No pude leer el plan: {e}", "hint": "Revisa la ruta del plan.json"})
    if isinstance(ops, dict) and "ops" in ops:
        ops = ops["ops"]
    dry_run = ("--dry-run" in args) or ("--yes" not in args)
    data = backend.plan(ops, dry_run=dry_run)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "plan", data=data)
    return make_result(False, "plan", error=data)
