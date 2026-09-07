from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


@dataclass
class Result:
    ok: bool
    command: str
    data: object = None
    error: dict | None = None
    format: OutputFormat = OutputFormat.TEXT

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "command": self.command,
            "data": self.data,
            "error": self.error,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        if self.error:
            return f"ERROR [{self.error.get('code', 'UNKNOWN')}]: {self.error.get('message', '')}\nHint: {self.error.get('hint', '')}"
        return str(self.data) if self.data is not None else "OK"

    def __str__(self) -> str:
        if self.format == OutputFormat.JSON:
            return self.to_json()
        return self.to_text()


@dataclass
class Error:
    code: str
    message: str
    hint: str

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "hint": self.hint}


class ExitCode(int, Enum):
    OK = 0
    USAGE = 2
    AUTH = 3
    NETWORK = 4
    NOT_FOUND = 5
    ABORTED = 6
    INTERNAL = 7


def make_result(ok: bool, command: str, data: object = None, error: dict | None = None, format: OutputFormat = OutputFormat.TEXT) -> Result:
    return Result(ok=ok, command=command, data=data, error=error, format=format)


def make_error(code: str, message: str, hint: str) -> Error:
    return Error(code=code, message=message, hint=hint)


class OutputFormatter:
    @staticmethod
    def format(result: Result) -> str:
        if result.format == OutputFormat.JSON:
            return result.to_json()
        return result.to_text()

    @staticmethod
    def exit_code(result: Result) -> int:
        if result.ok:
            return ExitCode.OK.value
        if result.error:
            code = result.error.get("code", "")
            mapping = {
                "AUTH": ExitCode.AUTH.value,
                "NETWORK": ExitCode.NETWORK.value,
                "NOT_FOUND": ExitCode.NOT_FOUND.value,
                "ABORTED": ExitCode.ABORTED.value,
                "USAGE": ExitCode.USAGE.value,
                "INTERNAL": ExitCode.INTERNAL.value,
            }
            return mapping.get(code, ExitCode.INTERNAL.value)
        return ExitCode.INTERNAL.value
