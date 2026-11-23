import json
import tomllib
from pathlib import Path

import pytest

from approval_gate import snippet

TOOLS = {"bm_project", "bm_read", "bm_search", "bm_write"}


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_snippet_prints_launcher_and_tool_permissions(
    client: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(snippet, "ROOT", Path("/example/check out"))
    monkeypatch.setattr(snippet.shutil, "which", lambda _: "/example/bin/uv")
    gate = "/example/configs/approval gate.json"
    expected = [
        "/example/bin/uv",
        "run",
        "--directory",
        "/example/check out",
        "--locked",
        "--no-sync",
        "python",
        "-m",
        "approval_gate.proxy",
        "--config",
        gate,
    ]

    status = snippet.main(["--client", client, "--config", gate])
    output = capsys.readouterr()

    assert status == 0
    assert not output.err
    if client == "codex":
        entry = tomllib.loads(output.out)["mcp_servers"]["basic_memory"]
        assert [entry["command"], *entry["args"]] == expected
        assert set(entry["enabled_tools"]) == TOOLS
    else:
        document = json.loads(output.out)
        entry = document["mcp"]["servers"]["basic_memory"]
        assert entry == {"type": "local", "command": expected, "codemode": False}
        deny, *allow = document["permissions"]
        assert deny == {"action": "basic_memory_*", "resource": "*", "effect": "deny"}
        assert {(rule["action"], rule["resource"], rule["effect"]) for rule in allow} == {
            (f"basic_memory_{tool}", "*", "allow") for tool in TOOLS
        }


def test_codex_snippet_rejects_emoji_in_config_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(snippet.shutil, "which", lambda _: "/example/bin/uv")

    with pytest.raises(SystemExit) as error:
        snippet.main(["--client", "codex", "--config", "/example/📁/gate.json"])

    output = capsys.readouterr()
    assert error.value.code == 2
    assert not output.out
    assert "gate configuration path contains a character outside" in output.err
    assert "use a path without emoji" in output.err
