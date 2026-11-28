import json
from pathlib import Path

import pytest

from shared_memory.approval_gate import launch
from shared_memory.approval_gate.native import NATIVE_ENV


def write_config(tmp_path: Path, env: dict[str, str]) -> Path:
    path = tmp_path / "gate.json"
    config = {
        "native_command": ["/example/bin/basic-memory", "mcp"],
        "proposals_dir": str(tmp_path / "approvals"),
        "audit_log": str(tmp_path / "audit.jsonl"),
        "env": env,
    }
    path.write_text(json.dumps(config))
    return path


@pytest.fixture
def state(tmp_path: Path) -> Path:
    state = tmp_path / "state"
    state.mkdir()
    (state / "config.json").write_text("{}")
    return state


@pytest.fixture(autouse=True)
def keep_umask(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    masks: list[int] = []
    monkeypatch.setattr(launch.os, "umask", masks.append)
    return masks


def test_mcp_launch_selects_fastembed_without_forcing_search_mode(tmp_path, state, monkeypatch, keep_umask):
    inherited = {
        "HOME": "/example/home",
        "PATH": "/example/bin",
        "TMPDIR": "/example/tmp",
        "LANG": "C",
        "LC_ALL": "C",
        "LC_CTYPE": "C",
    }
    monkeypatch.setattr(launch.os, "environ", inherited | {"UNRELATED_CLIENT_SETTING": "synthetic-value"})
    path = write_config(
        tmp_path,
        {
            "BASIC_MEMORY_CONFIG_DIR": str(state),
            "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "openai",
            "basic_memory_semantic_embedding_provider": "openai",
        },
    )
    calls = []
    monkeypatch.setattr(launch.os, "execvpe", lambda *call: calls.append(call))

    launch.mcp_main(["--config", str(path)])

    ((executable, command, env),) = calls
    assert executable == "/example/bin/basic-memory"
    assert command == ["/example/bin/basic-memory", "mcp"]
    assert env == inherited | {"BASIC_MEMORY_CONFIG_DIR": str(state)} | NATIVE_ENV
    assert env["BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER"] == "fastembed"
    assert "BASIC_MEMORY_DEFAULT_SEARCH_TYPE" not in env
    assert keep_umask == [0o077]


def test_launch_requires_a_configured_store(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "missing")})
    monkeypatch.setattr(launch.os, "execvpe", pytest.fail)

    with pytest.raises(SystemExit):
        launch.mcp_main(["--config", str(path)])

    assert "Shared memory is not configured" in capsys.readouterr().err


def test_launch_refuses_an_unpatched_runtime(tmp_path, state, monkeypatch, capsys):
    path = write_config(tmp_path, {"BASIC_MEMORY_CONFIG_DIR": str(state)})
    monkeypatch.setattr(launch, "BasicMemoryConfig", type("Unpatched", (), {"model_fields": {}}))
    monkeypatch.setattr(launch, "run_proxy", pytest.fail)

    with pytest.raises(SystemExit):
        launch.gate_main(["--config", str(path)])

    assert "patched runtime for MCP project creation" in capsys.readouterr().err


def test_launch_refuses_the_old_semantic_disable_runtime(tmp_path, state, monkeypatch, capsys):
    path = write_config(tmp_path, {"BASIC_MEMORY_CONFIG_DIR": str(state)})
    monkeypatch.setattr(
        launch,
        "BasicMemoryConfig",
        type("Legacy", (), {"model_fields": dict.fromkeys(("enable_mcp_project_create", "semantic_search_enabled"))}),
    )
    monkeypatch.setattr(launch.os, "execvpe", pytest.fail)

    with pytest.raises(SystemExit):
        launch.mcp_main(["--config", str(path)])

    error = capsys.readouterr().err
    assert "semantic-disable runtime" in error
    assert "uv sync --locked" in error


def test_gate_launch_passes_configured_store_to_the_proxy(tmp_path, state, monkeypatch):
    path = write_config(tmp_path, {"BASIC_MEMORY_CONFIG_DIR": str(state)})
    calls = []
    monkeypatch.setattr(launch, "run_proxy", lambda config, config_path: calls.append((config, config_path)) or 0)

    assert launch.gate_main(["--config", str(path)]) == 0

    ((config, config_path),) = calls
    assert config_path == path
    assert config.env == {"BASIC_MEMORY_CONFIG_DIR": str(state)}
