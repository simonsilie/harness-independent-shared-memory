import json
import subprocess
import sys
from pathlib import Path
from stat import S_IMODE
from unittest.mock import Mock

import pytest

from approval_gate import install, proxy
from approval_gate.config import Config


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


@pytest.mark.parametrize("invalid", ["proposals", "audit", "audit-parent", "overlapping", "inaccessible", None])
def test_check_config_validates_storage_paths_without_changing_them(tmp_path, monkeypatch, invalid):
    proposals = tmp_path / "store/approvals"
    audit = tmp_path / "logs/audit.jsonl"
    if invalid == "proposals":
        proposals.parent.mkdir()
        proposals.touch()
    elif invalid == "audit":
        audit.mkdir(parents=True)
    elif invalid == "audit-parent":
        audit.parent.touch()
    elif invalid == "overlapping":
        audit = proposals.parent
    elif invalid == "inaccessible":
        proposals.parent.mkdir()
        access = install.os.access
        monkeypatch.setattr(install.os, "access", lambda path, mode: path != proposals.parent and access(path, mode))
    config = tmp_path / "gate.json"
    config.write_text(
        Config(native_command=[sys.executable], proposals_dir=proposals, audit_log=audit).model_dump_json()
    )
    before = sorted(tmp_path.rglob("*"))

    if invalid:
        with pytest.raises(ValueError, match="Audit log|approval-gate directory"):
            install.check_config(config)
    else:
        install.check_config(config)

    assert sorted(tmp_path.rglob("*")) == before


@pytest.mark.parametrize("dry_run", [True, False])
def test_opencode_launcher_preserves_environment_placeholder(tmp_path, installer, monkeypatch, dry_run):
    args, run = installer
    old = "{env:HOME}/old-launcher"
    new = "{env:HOME}/new-launcher"
    original = f'''{{
  "mcp": {{"servers": {{"basic_memory": {{"type": "local", "command": ["{old}", /* keep */],
    "environment": {{"EXAMPLE": "placeholder"}}}}}}}}
  ,
  "lsp": {{"example": {{
    "command": ["{old}"],
    "url": "https://example.test/"
  }}}}
}}
'''
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
        test_call = next(call for call in run.call_args_list if "pytest" in call.args[0])
        launchers = json.loads(test_call.kwargs["env"]["SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS"])
        assert launchers == [{"command": str(tmp_path / "new-launcher"), "env": {"EXAMPLE": "placeholder"}}]
        assert config.read_text() == original.replace(old, new, 1)


def test_opencode_launcher_requires_matching_mcp_server(tmp_path, installer):
    args, run = installer
    path = tmp_path / "opencode.jsonc"
    original = '{"lsp": {"example": {"command": ["/example/old-launcher"]}}}\n'
    path.write_text(original)
    args.extend(["--replace-launcher", str(path), "/example/old-launcher", str(tmp_path / "new-launcher")])

    assert install.main() == 1
    run.assert_not_called()
    assert path.read_text() == original


@pytest.mark.parametrize("failure", ["handshake", "concurrent-edit"])
def test_launcher_migration_checks_every_file_before_switching(tmp_path, installer, failure):
    args, run = installer
    first, second = tmp_path / "first.toml", tmp_path / "second.toml"
    original = '[mcp_servers.basic_memory]\ncommand = "/example/old-launcher"\n'
    launcher = str(tmp_path / "new-launcher")
    wheel = tmp_path / "basic_memory-example.whl"
    wheel.touch()
    args.extend(["--wheel", str(wheel)])
    for path in (first, second):
        path.write_text(original)
        args.extend(["--replace-launcher", str(path), "/example/old-launcher", launcher])

    def finish_tests(command, **kwargs):
        if "-m" in command and "pytest" in command:
            env = kwargs["env"]
            assert json.loads(env["SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS"]) == [{"command": launcher, "env": {}}]
            assert env["SHARED_MEMORY_APPROVAL_CHECK_CONFIG"] == str(tmp_path / "gate.json")
            if failure == "handshake":
                raise subprocess.CalledProcessError(1, command)
            second.write_text(original + "# edited during tests\n")

    run.side_effect = finish_tests
    assert install.main() == 1
    assert first.read_text() == original
    assert second.read_text() == original + ("# edited during tests\n" if failure == "concurrent-edit" else "")
    (candidate_install,) = [call.args[0] for call in run.call_args_list if call.args[0][-1].endswith(wheel.name)]
    assert "--target" in candidate_install


def test_wheel_is_installed_in_live_environment_after_tests(tmp_path, installer):
    args, run = installer
    wheel = tmp_path / "basic_memory-example.whl"
    wheel.write_bytes(b"candidate")
    args.extend(["--wheel", str(wheel)])

    def mutate_source_after_tests(command, **kwargs):
        if "pytest" in command:
            wheel.write_bytes(b"changed")
        if command[-1].endswith(wheel.name):
            assert Path(command[-1]).read_bytes() == b"candidate"

    run.side_effect = mutate_source_after_tests

    assert install.main() == 0

    commands = [call.args[0] for call in run.call_args_list]
    candidate, live = [index for index, command in enumerate(commands) if command[-1].endswith(wheel.name)]
    tests = next(index for index, command in enumerate(commands) if "pytest" in command)
    assert candidate < tests < live
    assert "--target" in commands[candidate]
    assert "--target" not in commands[live]
    assert commands[candidate][-1] == commands[live][-1] != str(wheel)


@pytest.mark.parametrize("concurrent_edit", [False, True])
def test_launcher_migration_rolls_back_after_replacement_failure(tmp_path, installer, monkeypatch, concurrent_edit):
    args, _ = installer
    first, second = tmp_path / "first.toml", tmp_path / "second.toml"
    original = b'[mcp_servers.basic_memory]\r\ncommand = "/example/old-launcher"\r\n'
    launcher = str(tmp_path / "new-launcher")
    for path in (first, second):
        path.write_bytes(original)
        path.chmod(0o640)
        args.extend(["--replace-launcher", str(path), "/example/old-launcher", launcher])

    replace = Path.replace
    edited = original + b"# edited after the switch\r\n"

    def replace_or_fail(source, target):
        if target == second:
            assert launcher.encode() in first.read_bytes()
            if concurrent_edit:
                first.write_bytes(edited)
            raise PermissionError(target)
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", replace_or_fail)

    assert install.main() == 1
    assert first.read_bytes() == (edited if concurrent_edit else original)
    assert second.read_bytes() == original
    assert S_IMODE(first.stat().st_mode) == 0o640
    assert set(tmp_path.glob("tmp*")) == set()


@pytest.mark.parametrize("matches", [False, True])
def test_proxy_uses_selected_native_command_with_disposable_store(tmp_path, monkeypatch, matches):
    expected = tmp_path / "gate.json"
    disposable = tmp_path / "disposable.json"
    selected = expected if matches else tmp_path / "different.json"
    monkeypatch.setenv("SHARED_MEMORY_APPROVAL_CONFIG", str(selected))
    monkeypatch.setenv("SHARED_MEMORY_APPROVAL_CHECK_CONFIG", str(expected))
    monkeypatch.setenv("SHARED_MEMORY_APPROVAL_TEST_CONFIG", str(disposable))
    configured = Config(
        native_command=["configured", "argument"],
        proposals_dir=tmp_path / "live-approvals",
        audit_log=tmp_path / "live-audit.jsonl",
        env={"LAUNCHER_OPTION": "value", "BASIC_MEMORY_CONFIG_DIR": "/example/live/state"},
        ttl_hours=10,
    )
    test_config = Config(
        native_command=["fixture"],
        proposals_dir=tmp_path / "test-approvals",
        audit_log=tmp_path / "test-audit.jsonl",
        env={"BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "test-state")},
    )
    load_config = Mock(side_effect={expected: configured, disposable: test_config}.__getitem__)
    monkeypatch.setattr(proxy, "load_config", load_config)
    run_proxy = Mock(return_value=0)
    monkeypatch.setattr(proxy, "run_proxy", run_proxy)

    if matches:
        assert proxy.main([]) == 0
        active, active_path = run_proxy.call_args.args
        assert active_path == disposable
        assert active.native_command == configured.native_command
        assert active.ttl_hours == configured.ttl_hours
        assert active.env == {"LAUNCHER_OPTION": "value", **(test_config.env or {})}
        assert active.proposals_dir == test_config.proposals_dir
        assert active.audit_log == test_config.audit_log
    else:
        with pytest.raises(SystemExit) as error:
            proxy.main([])
        assert error.value.code == 2
        load_config.assert_not_called()
        run_proxy.assert_not_called()
