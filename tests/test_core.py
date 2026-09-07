from __future__ import annotations

import os
import sys

import pytest


def test_output_result_text():
    from mudctl.output import Result, OutputFormatter, make_result

    result = make_result(True, "test", data={"status": "ok"})
    text = OutputFormatter.format(result)
    assert "ok" in text.lower() or "True" in text


def test_output_result_json():
    from mudctl.output import Result, OutputFormatter, make_result

    result = make_result(True, "test", data={"status": "ok"}, format="json")
    json_str = OutputFormatter.format(result)
    assert '"ok": true' in json_str


def test_output_error():
    from mudctl.output import Result, OutputFormatter, make_result, make_error

    error = make_error("AUTH", "Autenticacion fallida", "Verifica credenciales")
    result = make_result(False, "doctor", error=error.to_dict())
    text = OutputFormatter.format(result)
    assert "ERROR" in text or "AUTH" in text


def test_exit_codes():
    from mudctl.output import ExitCode

    assert ExitCode.OK.value == 0
    assert ExitCode.USAGE.value == 2
    assert ExitCode.AUTH.value == 3
    assert ExitCode.NETWORK.value == 4
    assert ExitCode.NOT_FOUND.value == 5
    assert ExitCode.ABORTED.value == 6
    assert ExitCode.INTERNAL.value == 7


def test_utils_load_config():
    from mudctl.utils import load_config

    config = load_config()
    assert "host" in config
    assert "port" in config
    assert "user" in config
    assert config["host"] == "reinosdeleyenda.es"
    assert config["port"] == 3008
