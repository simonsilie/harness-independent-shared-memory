"""Planning and idempotency checks for the approval gate installer."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import pytest

from approval_gate import install

CODEX = """# machine settings
model = "gpt-5"

[mcp_servers.other]
command = "/usr/bin/other"

[mcp_servers.basic_memory]
command = "/old/.venv/bin/basic-memory"
args = [
  "mcp", "--transport", "stdio"
]
enabled_tools = ["bm_project", "bm_search"]

[mcp_servers.basic_memory.env]
BASIC_MEMORY_CONFIG_DIR = "/old/state"
"""

OPENCODE = """{
  // keep this comment
  "theme": "dark",
  "mcp": {
    "servers": {
      "basic_memory": {
        "type": "local",
        "command": ["/old/.venv/bin/basic-memory", "mcp", "--transport", "stdio"],
        "codemode": false,
        "environment": { "BASIC_MEMORY_CONFIG_DIR": "/old/state" }
      },
      "other": { "type": "local", "command": ["other"] }
    }
  },
  "permissions": [
    { "action": "shell", "resource": "*", "effect": "allow" },
    { "action": "basic_memory_bm_search", "resource": "*", "effect": "allow" }
  ]
}
"""


@pytest.fixture(autouse=True)
def temporary_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "checkout"
    for name in (".venv/bin/python", ".venv/bin/basic-memory"):
        executable = root / name
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text("")
        executable.chmod(0o755)
    monkeypatch.setattr(install, "ROOT", root)
    which = shutil.which
    monkeypatch.setattr(
        install.shutil, "which", lambda name, **kwargs: "/fake/bin/uv" if name == "uv" else which(name, **kwargs)
    )
    return root


def gate_config(tmp_path: Path, checkout: Path) -> Path:
    path = tmp_path / "gate.json"
    config: dict[str, Any] = {
        "native_command": [str(checkout / ".venv/bin/basic-memory"), "mcp", "--transport", "stdio"],
        "proposals_dir": "approvals",
        "audit_log": "audit.jsonl",
    }
    path.write_text(json.dumps(config))
    return path


def install_args(client: str, path: Path, gate: Path, apply: bool = False) -> list[str]:
    return [
        "--client",
        client,
        "--client-config",
        str(path),
        "--config",
        str(gate),
        *(["--apply"] if apply else []),
    ]


def test_preview_shows_diff_and_apply_writes_codex_entry(
    checkout: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(CODEX)
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args("codex", config, gate)) == 0
    preview = capsys.readouterr().out
    assert "--- a/" in preview and "+++ b/" in preview
    assert "Preview only" in preview
    assert config.read_text() == CODEX

    assert install.main(install_args("codex", config, gate, apply=True)) == 0
    updated = config.read_text()
    document = tomllib.loads(updated)
    server = document["mcp_servers"]["basic_memory"]
    assert server["command"] == "/fake/bin/uv"
    assert server["args"] == [
        "run",
        "--directory",
        str(checkout),
        "--locked",
        "--no-sync",
        "python",
        "-m",
        "approval_gate.proxy",
        "--config",
        str(gate),
    ]
    assert server["enabled_tools"] == ["bm_project", "bm_search"]
    assert document["mcp_servers"]["basic_memory"]["env"]["BASIC_MEMORY_CONFIG_DIR"] == "/old/state"
    assert "# machine settings" in updated
    assert '[mcp_servers.other]\ncommand = "/usr/bin/other"' in updated


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_existing_entry_is_migrated_without_losing_other_settings(client: str, checkout: Path, tmp_path: Path) -> None:
    config = tmp_path / ("config.toml" if client == "codex" else "opencode.jsonc")
    original = CODEX if client == "codex" else OPENCODE
    config.write_text(original)
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args(client, config, gate, apply=True)) == 0
    updated = config.read_text()
    if client == "codex":
        assert "[mcp_servers.other]" in updated
        assert "enabled_tools" in updated
        assert "BASIC_MEMORY_CONFIG_DIR" in updated
    else:
        document = json.loads(install._mask(updated))
        servers = document["mcp"]["servers"]
        assert servers["other"] == {"type": "local", "command": ["other"]}
        assert servers["basic_memory"]["environment"] == {"BASIC_MEMORY_CONFIG_DIR": "/old/state"}
        actions = {rule["action"] for rule in document["permissions"]}
        assert actions >= {"shell", "basic_memory_*", "basic_memory_bm_write"}
        assert "// keep this comment" in updated


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_repeated_installation_produces_no_diff(client: str, checkout: Path, tmp_path: Path) -> None:
    config = tmp_path / ("config.toml" if client == "codex" else "opencode.jsonc")
    config.write_text(CODEX if client == "codex" else OPENCODE)
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args(client, config, gate, apply=True)) == 0
    applied = config.read_bytes()
    assert install.main(install_args(client, config, gate)) == 0
    assert config.read_bytes() == applied


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_fresh_configuration_gets_a_complete_entry(client: str, checkout: Path, tmp_path: Path) -> None:
    config = tmp_path / ("config.toml" if client == "codex" else "opencode.jsonc")
    config.write_text("")
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args(client, config, gate, apply=True)) == 0
    text = config.read_text()
    if client == "codex":
        server = tomllib.loads(text)["mcp_servers"]["basic_memory"]
        assert server["enabled_tools"] == list(install.TOOLS)
    else:
        document = json.loads(install._mask(text))
        assert document["mcp"]["servers"]["basic_memory"]["type"] == "local"
        assert len(document["permissions"]) == 5


def test_documented_launcher_reports_missing_runtime_before_writing(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required to verify the documented launcher")
    root = tmp_path / "fresh-checkout"
    package = root / "approval_gate"
    package.mkdir(parents=True)
    for name in ("__init__.py", "install.py", "config.py"):
        shutil.copyfile(install.ROOT / "approval_gate" / name, package / name)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(install.ROOT / name, root / name)
    config = tmp_path / "config.toml"
    config.write_text(CODEX)
    gate = gate_config(tmp_path, root)

    result = subprocess.run(
        [
            uv,
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "approval_gate.install",
            *install_args("codex", config, gate, apply=True),
        ],
        cwd=root,
        env=os.environ
        | {
            "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
            "UV_OFFLINE": "1",
            "UV_PROJECT_ENVIRONMENT": ".venv",
            "UV_PYTHON": sys.executable,
            "UV_PYTHON_DOWNLOADS": "never",
        },
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert "uv sync --locked" in result.stderr
    assert config.read_text() == CODEX


@pytest.mark.parametrize(
    "following",
    [
        '[mcp_servers.other]\ncommand = "other"\nargs = ["unchanged"]\n',
        '[mcp_servers.basic_memory.env]\nSTORE = "unchanged"\n',
        '[[agents]]\ncommand = "other"\nargs = ["unchanged"]\n',
        "",
    ],
)
def test_codex_inserts_missing_args_into_basic_memory_table_only(following: str) -> None:
    original = "[mcp_servers.\"basic_memory\"]\ndescription = '''\n[not_a_table]\n'''\ncommand = \"native\"" + (
        "\n\n" + following if following else ""
    )
    expected = tomllib.loads(original)
    expected["mcp_servers"]["basic_memory"].update(command="uv", args=["run"])

    updated = install.plan_toml(original, "uv", ["run"])

    assert tomllib.loads(updated) == expected
    assert updated.endswith(following)
    assert install.plan_toml(updated, "uv", ["run"]) == updated


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        ([("basic_memory_bm_write", "deny"), ("basic_memory_bm_search", "allow")], ["deny", "allow", "allow", "deny"]),
        ([("basic_memory_*", "deny"), ("basic_memory_bm_search", "allow")], ["deny", "allow", "deny", "deny"]),
        ([("shell", "deny")], ["allow", "allow", "allow", "deny"]),
    ],
)
def test_opencode_defaults_preserve_existing_permission_precedence(
    rules: list[tuple[str, str]], expected: list[str]
) -> None:
    existing = [{"action": action, "resource": "*", "effect": effect} for action, effect in rules]
    original = json.dumps({"permissions": existing})
    updated = install.plan_jsonc(original, "uv", ["run"])
    permissions = json.loads(install._mask(updated))["permissions"]
    actions = [f"basic_memory_{tool}" for tool in ("bm_write", "bm_search", "bm_read", "bm_delete")]

    assert [
        next(rule["effect"] for rule in reversed(permissions) if fnmatchcase(action, rule["action"]))
        for action in actions
    ] == expected
    assert permissions[-len(existing) :] == existing
    assert install.plan_jsonc(updated, "uv", ["run"]) == updated


def test_opencode_keeps_comments_after_trailing_commas() -> None:
    original = """{
  "mcp": {"servers": {"other": {"type": "local", "command": ["other"]}, /* keep block */}},
  "permissions": [{"action": "shell", "resource": "*", "effect": "deny"}, // keep line
  ],
  "theme": "dark",
}
"""
    updated = install.plan_jsonc(original, "uv", ["run"])
    document = json.loads(install._mask(updated))

    assert document["mcp"]["servers"]["other"]["command"] == ["other"]
    assert document["mcp"]["servers"]["basic_memory"]["command"] == ["uv", "run"]
    assert document["theme"] == "dark"
    assert "/* keep block */" in updated
    assert "// keep line" in updated
    assert install.plan_jsonc(updated, "uv", ["run"]) == updated


def test_apply_updates_the_target_of_a_relative_symlink(checkout: Path, tmp_path: Path) -> None:
    target = tmp_path / "dotfiles.jsonc"
    target.write_text(OPENCODE)
    target.chmod(0o640)
    config = tmp_path / "opencode.jsonc"
    config.symlink_to(target.name)
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args("opencode", config, gate, apply=True)) == 0

    assert config.readlink() == Path(target.name)
    document = json.loads(install._mask(target.read_text()))
    assert document["mcp"]["servers"]["basic_memory"]["command"][0] == "/fake/bin/uv"
    assert target.stat().st_mode & 0o777 == 0o640


def test_codex_migrates_the_assignment_outside_multiline_arguments(checkout: Path, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text("""[mcp_servers.basic_memory]
args = [
    '''
command = "argument text"
''', # closing bracket ] in a comment
]
command = "/native#path" # keep this comment
""")
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args("codex", config, gate, apply=True)) == 0
    updated = config.read_text()
    server = tomllib.loads(updated)["mcp_servers"]["basic_memory"]
    assert server["command"] == "/fake/bin/uv"
    assert server["args"][5:8] == ["python", "-m", "approval_gate.proxy"]
    assert "# keep this comment" in updated


def test_opencode_migrates_escaped_keys_and_preserves_existing_policies() -> None:
    original = (
        OPENCODE.replace('"mcp"', r'"\u006dcp"')
        .replace('"permissions"', r'"\u0070ermissions"')
        .replace('"command"', r'"\u0063ommand"')
        .replace(
            '"basic_memory_bm_search", "resource": "*", "effect": "allow"',
            '"basic_memory_bm_write", "resource": "*", "effect": "deny"',
        )
    )

    updated = install.plan_jsonc(original, "uv", ["run"])
    document = json.loads(install._mask(updated))
    servers = document["mcp"]["servers"]
    assert servers["basic_memory"]["command"] == ["uv", "run"]
    assert servers["other"]["command"] == ["other"]
    assert document["permissions"][-1] == {"action": "basic_memory_bm_write", "resource": "*", "effect": "deny"}
    assert install.plan_jsonc(updated, "uv", ["run"]) == updated


@pytest.mark.parametrize(
    ("original", "error"),
    [
        (
            '{"mcp":{"servers":{"basic_memory":{"type":"remote","url":"https://example.invalid/mcp"}}}}',
            "Only local OpenCode",
        ),
        (r'{"mcp":{},"\u006dcp":{}}', "Duplicate OpenCode setting 'mcp'"),
    ],
)
def test_opencode_rejects_unsupported_migrations_without_changes(
    checkout: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], original: str, error: str
) -> None:
    config = tmp_path / "opencode.jsonc"
    config.write_text(original)
    gate = gate_config(tmp_path, checkout)

    assert install.main(install_args("opencode", config, gate, apply=True)) == 1
    assert error in capsys.readouterr().err
    assert config.read_text() == original


def test_codex_rejects_http_migrations_without_changes(
    checkout: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    original = '[mcp_servers.basic_memory]\nurl = "https://example.invalid/mcp"\n'
    config = tmp_path / "config.toml"
    config.write_text(original)

    assert install.main(install_args("codex", config, gate_config(tmp_path, checkout), apply=True)) == 1
    assert "Only stdio Codex" in capsys.readouterr().err
    assert config.read_text() == original


@pytest.mark.parametrize("executable", ["./missing/basic-memory", "missing-basic-memory"])
def test_missing_native_executable_aborts_before_writing(
    checkout: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], executable: str
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(CODEX)
    gate = gate_config(tmp_path, checkout)
    data = json.loads(gate.read_text())
    data["native_command"] = [executable, "mcp"]
    data["env"] = {"PATH": str(checkout / ".venv/bin")}
    gate.write_text(json.dumps(data))

    assert install.main(install_args("codex", config, gate, apply=True)) == 1
    assert "Native executable" in capsys.readouterr().err
    assert config.read_text() == CODEX


def test_codex_keeps_comments_inside_multiline_arguments() -> None:
    original = """[mcp_servers.basic_memory]
command = "/native"
args = [
  # keep local scope
  "mcp#argument", # keep this # entire comment
  '''
# part of an argument
''',
]
"""
    updated = install.plan_toml(original, "uv", ["run"])

    assert tomllib.loads(updated)["mcp_servers"]["basic_memory"]["args"] == ["run"]
    assert "# keep local scope" in updated
    assert "# keep this # entire comment" in updated
    assert "# part of an argument" not in updated
    assert install.plan_toml(updated, "uv", ["run"]) == updated
