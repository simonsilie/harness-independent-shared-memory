import sys
from unittest.mock import Mock

import pytest

from approval_gate import install


@pytest.fixture
def installer(tmp_path, monkeypatch):
    for name in ("python", "basic-memory", "uv", "new-launcher"):
        executable = tmp_path / name
        executable.touch(mode=0o700)
    config = tmp_path / "gate.json"
    config.write_text("{}")
    args = ["install.py", "--python", str(tmp_path / "python"), "--config", str(config)]
    run = Mock()
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(install.subprocess, "run", run)
    monkeypatch.setenv("PATH", str(tmp_path))
    return args, run


def test_missing_launcher_stops_before_installation_or_configuration_changes(tmp_path, installer, capsys):
    args, run = installer
    original = '[mcp_servers.basic_memory]\ncommand = "/example/old-launcher"\n'
    for filename, launcher in (("first.toml", "new-launcher"), ("second.toml", "missing-launcher")):
        config = tmp_path / filename
        config.write_text(original)
        args.extend(["--replace-launcher", str(config), "/example/old-launcher", str(tmp_path / launcher)])

    assert install.main() == 1
    assert "missing-launcher" in capsys.readouterr().err
    run.assert_not_called()
    assert (tmp_path / "first.toml").read_text() == original
    assert (tmp_path / "second.toml").read_text() == original


@pytest.mark.parametrize("dry_run", [True, False])
def test_opencode_launcher_preserves_environment_placeholder(tmp_path, installer, monkeypatch, dry_run):
    args, run = installer
    old = "{env:HOME}/old-launcher"
    new = "{env:HOME}/new-launcher"
    original = '{\n  "mcp": {\n    "basic_memory": {\n      "command": ["' + old + '"]\n    }\n  }\n}\n'
    config = tmp_path / "opencode.jsonc"
    config.write_text(original)
    monkeypatch.setenv("HOME", str(tmp_path))
    args.extend(["--replace-launcher", str(config), old, new])
    if dry_run:
        args.append("--dry-run")

    assert install.main() == 0
    if dry_run:
        run.assert_not_called()
        assert config.read_text() == original
    else:
        assert run.called
        assert config.read_text() == original.replace(old, new)
