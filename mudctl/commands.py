from __future__ import annotations

import sys
from typing import Callable

from mudctl.backend import FTPClientBackend, FTPBackend
from mudctl.errors import AuthenticationError, NetworkError
from mudctl.output import Result, OutputFormatter, ExitCode, make_result, make_error


def run(backend: FTPBackend, argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
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

    print(OutputFormatter.format(result))
    return OutputFormatter.exit_code(result)


def handle_doctor(backend: FTPBackend) -> Result:
    data = backend.doctor()
    if data.get("status") == "ok":
        return make_result(True, "doctor", data=data)
    return make_result(False, "doctor", error=data)


def handle_list(backend: FTPBackend, args: list[str]) -> Result:
    path = args[0] if args else "/"
    recursive = "--recursive" in args
    depth = None
    for i, a in enumerate(args):
        if a == "--depth" and i + 1 < len(args):
            depth = int(args[i + 1])
    data = backend.list(path, recursive=recursive, depth=depth)
    return make_result(True, "list", data=data)


def handle_get(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "get", error={"code": "USAGE", "message": "Usage: mudctl get <remote_path> [local_path]", "hint": "Provide at least the remote path."})
    remote_path = args[0]
    local_path = args[1] if len(args) > 1 else None
    data = backend.get(remote_path, local_path)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "get", data=data)
    return make_result(False, "get", error=data)


def handle_put(backend: FTPBackend, args: list[str]) -> Result:
    if len(args) < 2:
        return make_result(False, "put", error={"code": "USAGE", "message": "Usage: mudctl put <local_path> <remote_path> [--dry-run] [--yes] [--expect N]", "hint": "Provide local and remote paths."})
    local_path = args[0]
    remote_path = args[1]
    dry_run = "--dry-run" in args
    yes = "--yes" in args
    expect = None
    for i, a in enumerate(args):
        if a == "--expect" and i + 1 < len(args):
            expect = int(args[i + 1])
    data = backend.put(local_path, remote_path, dry_run=dry_run)
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
        return make_result(False, "mkdir", error={"code": "USAGE", "message": "Usage: mudctl mkdir <path> [--parents]", "hint": "Provide at least the path."})
    path = args[0]
    parents = "--parents" in args
    data = backend.mkdir(path, parents=parents)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "mkdir", data=data)
    return make_result(False, "mkdir", error=data)


def handle_rm(backend: FTPBackend, args: list[str]) -> Result:
    if not args:
        return make_result(False, "rm", error={"code": "USAGE", "message": "Usage: mudctl rm <path> [--recursive] [--dry-run] [--yes] [--expect N] [--max N]", "hint": "Provide at least the path."})
    path = args[0]
    recursive = "--recursive" in args
    dry_run = "--dry-run" in args
    yes = "--yes" in args
    expect = None
    max_files = None
    for i, a in enumerate(args):
        if a == "--expect" and i + 1 < len(args):
            expect = int(args[i + 1])
        if a == "--max" and i + 1 < len(args):
            max_files = int(args[i + 1])
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
        return make_result(False, "move", error={"code": "USAGE", "message": "Usage: mudctl move <source> <destination>", "hint": "Provide source and destination."})
    source = args[0]
    destination = args[1]
    data = backend.move(source, destination)
    if "status" in data and data["status"] == "ok":
        return make_result(True, "move", data=data)
    return make_result(False, "move", error=data)
