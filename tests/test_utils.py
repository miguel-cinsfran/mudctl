from __future__ import annotations


def test_load_config():
    import os
    # Guardar estado del entorno para no afectar a otros tests
    old = {k: os.environ.get(k) for k in ("MUD_HOST", "MUD_PORT", "MUD_USER",
                                           "MUD_PASSWORD", "MUD_PROTOCOL",
                                           "MUD_TIMEOUT", "MUD_ENCODING",
                                           "MUD_ROOT", "MUD_HOME")}
    for k in old:
        os.environ.pop(k, None)
    try:
        from mudctl.utils import load_config
        config = load_config()
        assert config["host"] == "reinosdeleyenda.es"
        assert config["port"] == 3008
        assert config["user"] == "hazrakh"
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_env_loading():
    import os
    os.environ["MUD_HOST"] = "reinosdeleyenda.es"
    from mudctl.utils import _env
    assert _env("MUD_HOST") == "reinosdeleyenda.es"


def test_require_credential_missing():
    from mudctl.utils import require_credential
    from mudctl.errors import AuthenticationError
    try:
        require_credential("PASSWORD")
    except AuthenticationError as e:
        assert e.code == "AUTH"


def test_exit_codes():
    from mudctl.output import ExitCode
    assert ExitCode.OK.value == 0
    assert ExitCode.AUTH.value == 3
    assert ExitCode.NETWORK.value == 4


def test_result_text():
    from mudctl.output import make_result, OutputFormatter
    result = make_result(True, "doctor", data={"status": "ok"})
    text = OutputFormatter.format(result)
    assert text is not None


def test_result_json():
    from mudctl.output import make_result, OutputFormatter
    result = make_result(True, "list", data=[{"name": "file.c"}], format="json")
    json_str = OutputFormatter.format(result)
    assert "file.c" in json_str


def test_make_error():
    from mudctl.output import make_error, OutputFormatter
    error = make_error("AUTH", "Autenticacion fallida", "Verifica credenciales")
    assert error.code == "AUTH"
    assert error.hint == "Verifica credenciales"