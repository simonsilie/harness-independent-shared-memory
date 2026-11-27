import contextlib
import importlib.util
import io
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "evaluation/claude/run.py"


def load_runner(tmp_path):
    spec = importlib.util.spec_from_file_location("claude_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    root = tmp_path
    for folder in ("evaluation/claude", "evaluation/corpus"):
        (root / folder).mkdir(parents=True)
    (root / "evaluation/claude/mcp.json").write_text('{"mcpServers": {"basic_memory": {}}}')
    (root / "evaluation/claude/settings.json").write_text('{"permissions": {"allow": [], "deny": []}}')
    (root / "evaluation/questions.json").write_text("[]")
    setattr(runner, "ROOT", root)
    return runner, root / "evaluation/claude/runs/check"


def init_event(tools=("mcp__basic_memory__bm_read", "mcp__basic_memory__bm_search"), connected=True):
    return {
        "type": "system",
        "subtype": "init",
        "tools": list(tools),
        "mcp_servers": [{"name": "basic_memory", "status": "connected" if connected else "failed"}],
    }


def result_event(response="[]"):
    return {"type": "result", "subtype": "success", "is_error": False, "result": response}


def run_cli(runner, out, argv, preflight_tools=None, run_tools=None):
    """Run the runner with a fake Claude CLI; return (invocations, files written at each call)."""
    preflight_tools = preflight_tools if preflight_tools is not None else init_event()["tools"]
    run_tools = run_tools if run_tools is not None else init_event()["tools"]
    invocations = []
    snapshots = []

    def fake_run(command, **kwargs):
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "2.1.323", "")
        settings = Path(command[command.index("--settings") + 1])
        preflight = settings.name == "preflight-settings.json"
        invocations.append({"preflight": preflight, "prompt": command[-1], "settings": settings})
        events: list[dict[str, Any]] = [init_event(tools=preflight_tools if preflight else run_tools)]
        if not preflight:
            events.append(result_event())
        kwargs["stdout"].write("\n".join(json.dumps(event) for event in events) + "\n")
        snapshots.append(
            {
                "effective_tools": (out / "effective-tools.json").exists(),
                "client_response": (out / "client-response.txt").exists(),
            }
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch.object(runner.subprocess, "run", side_effect=fake_run),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        runner.main(argv, out)
    return invocations, snapshots


def test_unexpected_preflight_tool_stops_before_model_request(tmp_path):
    runner, out = load_runner(tmp_path)
    tools = [*init_event()["tools"], "mcp__basic_memory__bm_write"]

    with pytest.raises(SystemExit, match="Effective tool inventory failed"):
        run_cli(runner, out, [], preflight_tools=tools)

    preflight = json.loads((out / "preflight-events.jsonl").read_text().splitlines()[0])
    assert set(preflight["tools"]) == set(tools)
    assert not (out / "events.jsonl").exists()
    assert not (out / "prompt.txt").exists()
    assert not (out / "client-response.txt").exists()


def test_normal_run_verifies_inventory_before_model_request(tmp_path):
    runner, out = load_runner(tmp_path)

    invocations, snapshots = run_cli(runner, out, [])

    assert len(invocations) == 2
    assert invocations[0]["preflight"] and invocations[0]["prompt"] == "Check readiness."
    assert not invocations[1]["preflight"] and invocations[1]["prompt"].startswith("Answer each of these 22")
    assert snapshots[1]["effective_tools"] and not snapshots[1]["client_response"]
    assert (out / "client-response.txt").read_text() == "[]"
    assert json.loads((out / "preflight-settings.json").read_text())["hooks"]
    assert "hooks" not in json.loads((out / "client-settings.json").read_text())


def test_extra_tool_in_evaluated_run_stops_before_response(tmp_path):
    runner, out = load_runner(tmp_path)
    tools = [*init_event()["tools"], "mcp__basic_memory__bm_write"]

    with pytest.raises(SystemExit, match="Effective tool inventory failed"):
        run_cli(runner, out, [], run_tools=tools)

    assert (out / "events.jsonl").exists()
    assert not (out / "client-response.txt").exists()


def test_verify_only_stops_after_single_preflight(tmp_path):
    runner, out = load_runner(tmp_path)

    invocations, _ = run_cli(runner, out, ["--verify-only"])

    assert len(invocations) == 1
    assert invocations[0]["preflight"]
    assert (out / "effective-tools.json").exists()


def test_startup_run_uses_preflight_and_startup_turn(tmp_path):
    runner, out = load_runner(tmp_path)

    invocations, _ = run_cli(runner, out, ["--startup"])

    assert len(invocations) == 2
    assert invocations[0]["preflight"] and invocations[0]["prompt"] == "Check readiness."
    assert not invocations[1]["preflight"] and invocations[1]["prompt"] == runner.STARTUP_PROMPT
    assert (out / "instructions.txt").read_text() == runner.STARTUP_INSTRUCTIONS
    assert (out / "client-response.txt").read_text() == "[]"
