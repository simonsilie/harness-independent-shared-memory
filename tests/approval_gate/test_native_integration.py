"""End-to-end gate check against a disposable native Basic Memory store."""

import asyncio
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from approval_gate import ProposalError, cli
from approval_gate.config import Config
from approval_gate.proposals import list_proposals

DURABLE = (
    "---\ntitle: Gated decision\nkind: durable\nstatus: active\nsource: integration check\n---\n\nKeep SQLite local.\n"
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("APPROVAL_GATE_TEST_SECRET", "synthetic-credential")
    root = tmp_path / "store"
    state = root / "state"
    personal = root / "notes/personal"
    alpha = root / "notes/alpha"
    for folder in (state, personal / "durable", personal / "temporary", personal / "handovers", alpha / "handovers"):
        folder.mkdir(parents=True)
    (personal / "handovers/existing-durable.md").write_text(DURABLE)
    (alpha / "handovers/launcher-probe.md").write_text(DURABLE)
    config = {
        "projects": {
            "personal": {"path": str(personal), "mode": "local"},
            "alpha": {"path": str(alpha), "mode": "local"},
        },
        "default_project": "personal",
        "database_backend": "sqlite",
        "database_url": None,
        "default_search_type": "text",
        "semantic_search_enabled": False,
        "auto_update": False,
        "logfire_enabled": False,
    }
    (state / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    env = {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(personal),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED": "false",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "FASTMCP_CHECK_FOR_UPDATES": "off",
        "HF_HUB_OFFLINE": "1",
    }
    executable = Path(
        os.environ.get("SHARED_MEMORY_APPROVAL_TEST_NATIVE", Path(sys.executable).with_name("basic-memory"))
    )
    if "SHARED_MEMORY_APPROVAL_TEST_NATIVE" in os.environ:
        env["PYTHONPATH"] = os.environ["PYTHONPATH"]
    subprocess.run(
        [str(executable), "reindex", "--full", "--search"],
        env=get_default_environment() | env,
        check=True,
        capture_output=True,
        timeout=180,
    )
    return root, executable, env


@pytest.fixture
def gate_config(store, tmp_path):
    root, executable, environment = store
    config = Config(
        native_command=[str(executable), "mcp", "--transport", "stdio"],
        proposals_dir=tmp_path / "approvals",
        audit_log=tmp_path / "audit.jsonl",
        env=environment,
    )
    config_path = tmp_path / "gate.json"
    config_path.write_text(config.model_dump_json())
    assert "APPROVAL_GATE_TEST_SECRET" not in json.loads(config_path.read_text())["env"]
    return root, config, config_path


@pytest.fixture
def proxy(gate_config):
    root, config, config_path = gate_config
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "approval_gate.proxy", "--config", str(config_path)],
        cwd=Path(__file__).resolve().parents[2],
        env={"PYTHONPATH": os.environ.get("PYTHONPATH", "")},
    )
    return root, config, parameters


@pytest.mark.parametrize(
    "launcher", json.loads(os.environ.get("SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS", "[]")) or [None]
)
def test_replacement_launcher_uses_disposable_gate(gate_config, tmp_path, launcher):
    root, config, config_path = gate_config
    home = tmp_path / "home"
    home.mkdir()
    (home / "SharedMemory").symlink_to(root, target_is_directory=True)
    projects = home / "Projects"
    projects.mkdir()
    checkout = Path(__file__).resolve().parents[2]
    (projects / "harness-independent-shared-memory").symlink_to(checkout, target_is_directory=True)
    test_env = {
        **(config.env or {}),
        "HOME": str(home),
        "BASIC_MEMORY_CLOUD_MODE": "false",
        "BASIC_MEMORY_FORCE_CLOUD": "false",
        "BASIC_MEMORY_DATABASE_BACKEND": "sqlite",
        "BASIC_MEMORY_DATABASE_URL": "",
        "BASIC_MEMORY_PROJECT_ROOT": "",
        "BASIC_MEMORY_MCP_PROJECT": "alpha",
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
    }
    config_path.write_text(config.model_copy(update={"env": test_env}).model_dump_json())
    selected_path = os.environ.get("SHARED_MEMORY_APPROVAL_CHECK_CONFIG")
    expected = selected_path or str(tmp_path / "launcher-config.json")
    if launcher is None:
        wrapper = tmp_path / "launcher"
        if selected_path is None:
            native = tmp_path / "native"
            native.write_text(
                "#!/bin/sh\nset -eu\n"
                'test "$APPROVAL_GATE_NATIVE_MODE" = local\n'
                'test "$BASIC_MEMORY_MCP_PROJECT" = alpha\n'
                'test "$1" = expected-argument\n'
                'test -f "$HOME/SharedMemory/state/config.json"\n'
                'export BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemory/state"\n'
                ': > "$HOME/native-started"\n'
                "shift\n"
                f'exec {shlex.join(config.native_command)} "$@"\n'
            )
            native.chmod(0o700)
            selected = config.model_copy(
                update={
                    "native_command": [str(native), "expected-argument"],
                    "proposals_dir": tmp_path / "live-approvals",
                    "audit_log": tmp_path / "live-audit.jsonl",
                    "env": {
                        "APPROVAL_GATE_NATIVE_MODE": "local",
                        "BASIC_MEMORY_CONFIG_DIR": "/example/live/state",
                        "BASIC_MEMORY_MCP_PROJECT": "example-live-project",
                    },
                }
            )
            Path(expected).write_text(selected.model_dump_json())
        command = shlex.join([sys.executable, "-m", "approval_gate.proxy", "--config", expected])
        wrapper.write_text(
            "#!/bin/sh\nset -eu\n"
            'test -f "$HOME/SharedMemory/state/config.json"\n'
            f'test "$BASIC_MEMORY_CONFIG_DIR" = {shlex.quote(str(root / "state"))}\n'
            ': > "$HOME/launcher-started"\n'
            f'cd {shlex.quote(str(checkout))} && exec {command} "$@"\n'
        )
        wrapper.chmod(0o700)
        launcher = {"command": str(wrapper), "env": {}}
    env = {
        **launcher["env"],
        **test_env,
        "SHARED_MEMORY_APPROVAL_CHECK_CONFIG": expected,
        "SHARED_MEMORY_APPROVAL_CHECK_PREFIX": sys.prefix,
        "SHARED_MEMORY_APPROVAL_TEST_CONFIG": str(config_path),
    }
    if staged_packages := os.environ.get("SHARED_MEMORY_APPROVAL_TEST_PACKAGES"):
        env["PYTHONPATH"] = os.pathsep.join(filter(None, (staged_packages, launcher["env"].get("PYTHONPATH"))))
    parameters = StdioServerParameters(
        command=launcher["command"],
        cwd=launcher.get("cwd", tmp_path),
        env=env,
    )

    async def check():
        async with (
            asyncio.timeout(45),
            stdio_client(parameters) as streams,
            ClientSession(*streams, read_timeout_seconds=30) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"bm_project", "bm_read", "bm_search", "bm_write"}
            note = await session.call_tool("bm_read", {"project": "alpha", "identifier": "handovers/launcher-probe.md"})
            assert not note.is_error and any(
                "Keep SQLite local." in block.text for block in note.content if hasattr(block, "text")
            )

    asyncio.run(check())
    assert config.proposals_dir.is_dir()
    if selected_path is None:
        assert (home / "launcher-started").is_file()
        assert (home / "native-started").is_file()
        assert not (tmp_path / "live-approvals").exists()


def test_durable_write_requires_owner_approval_and_then_persists(proxy):
    root, config, parameters = proxy
    target = root / "notes/personal/durable/decision.md"
    arguments = {"content": DURABLE, "project": "personal", "identifier": "personal/durable/decision"}

    async def propose():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"bm_project", "bm_read", "bm_search", "bm_write"}
            return await session.call_tool("bm_write", arguments)

    result = asyncio.run(propose())
    assert not result.is_error
    assert not target.exists()
    (proposal,) = list_proposals(config)
    assert result.structured_content["result"]["proposal_id"] == proposal["id"]
    assert proposal["arguments"]["identifier"] == "durable/decision.md"
    constrained = config.model_copy(update={"env": (config.env or {}) | {"BASIC_MEMORY_MCP_PROJECT": "alpha"}})

    with pytest.raises(ProposalError, match="address the approved project UUID"):
        cli.command_approve(constrained, proposal["id"], confirm=lambda _: True)

    assert list_proposals(config)[0]["status"] == "pending"
    assert not target.exists()
    assert not (root / "notes/alpha/durable/decision.md").exists()
    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0

    assert target.exists()
    assert target.read_text().startswith("---\ntitle: Gated decision")
    assert list_proposals(config)[0]["status"] == "approved"


def test_approval_requires_the_accepted_markdown_revision(proxy):
    root, config, parameters = proxy
    blocked_folder = root / "notes/personal/blocked"
    blocked_folder.write_text("This path is a regular file.")
    arguments = {"content": DURABLE, "project": "personal", "identifier": "blocked/decision.md"}

    async def propose():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            return await session.call_tool("bm_write", arguments)

    result = asyncio.run(propose())
    assert not result.is_error, result.content
    (proposal,) = list_proposals(config)

    with pytest.raises(ProposalError, match="Check the native store.*Could not verify the accepted Markdown revision"):
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    assert list_proposals(config)[0]["status"] == "outcome_unknown"
    assert not (blocked_folder / "decision.md").exists()


@pytest.mark.parametrize(
    ("updates", "code"),
    [({}, "ALREADY_EXISTS"), ({"expected_checksum": "stale-checksum"}, "REVISION_CONFLICT")],
)
def test_approval_records_definite_write_refusal(proxy, updates, code, capsys):
    root, config, parameters = proxy
    identifier = "handovers/existing-durable.md"
    target = root / "notes/personal" / identifier
    before = target.read_bytes()
    arguments = {"content": DURABLE + "\nUpdated content.\n", "project": "personal", "identifier": identifier}

    async def propose():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            return await session.call_tool("bm_write", arguments | updates)

    result = asyncio.run(propose())
    assert not result.is_error, result.content
    (proposal,) = list_proposals(config)

    with pytest.raises(ProposalError, match=f"^Native bm_write refused \\({code}\\):"):
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    assert list_proposals(config)[0]["status"] == "refused"
    assert target.read_bytes() == before
    assert json.loads(config.audit_log.read_text().splitlines()[-1])["event"] == "proposal_refused"
    capsys.readouterr()
    assert cli.command_list(config) == 0
    assert proposal["id"] not in capsys.readouterr().out


def test_temporary_handover_lifecycle_uses_the_proxy(proxy):
    root, config, parameters = proxy
    target = root / "notes/personal/handovers/integration.md"
    arguments = {
        "content": (
            "---\ntitle: Integration handover\nkind: temporary\nstatus: active\nlast_activity: '2000-01-01T00:00:00Z'\n"
            "---\n\nResume this work.\n"
        ),
        "project": "personal",
        "identifier": "/handovers/integration.md",
    }

    async def wait_for_content(*lines):
        # Native file materialization can finish after the MCP response.
        async with asyncio.timeout(5):
            while True:
                content = target.read_text() if target.exists() else ""
                if all(line in content for line in lines):
                    return
                await asyncio.sleep(0.05)

    async def verify():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            created = await session.call_tool("bm_write", arguments)
            assert not created.is_error, created.content
            assert list_proposals(config) == []
            await wait_for_content("Resume this work.")

            for status in ("completed", "archived", "active"):
                read = await session.call_tool(
                    "bm_read",
                    {"identifier": arguments["identifier"], "project": "personal", "output_format": "json"},
                )
                assert not read.is_error and isinstance(read.structured_content, dict), read.content
                note = read.structured_content.get("result", read.structured_content)
                status_fields = f"status: {status}"
                if status == "archived":
                    status_fields += "\narchive_reason: completed"
                if status == "active":
                    status_fields += "\narchive_reason: null"
                content = arguments["content"].replace("status: active", status_fields)
                changed = await session.call_tool(
                    "bm_write", arguments | {"expected_checksum": note["checksum"], "content": content}
                )
                assert not changed.is_error, changed.content
                assert list_proposals(config) == []
                await wait_for_content(*status_fields.splitlines())

            proposed = await session.call_tool(
                "bm_write",
                arguments | {"identifier": "handovers/durable.md", "metadata": {"kind": "durable"}},
            )
            assert not proposed.is_error, proposed.content
            assert not target.with_name("durable.md").exists()

            existing = target.with_name("existing-durable.md")
            before = existing.read_bytes()
            read = await session.call_tool(
                "bm_read",
                {"identifier": "handovers/existing-durable.md", "project": "personal", "output_format": "json"},
            )
            assert not read.is_error and isinstance(read.structured_content, dict), read.content
            note = read.structured_content.get("result", read.structured_content)
            proposed = await session.call_tool(
                "bm_write",
                arguments | {"identifier": "handovers/existing-durable.md", "expected_checksum": note["checksum"]},
            )
            assert not proposed.is_error, proposed.content
            assert existing.read_bytes() == before
            assert len(list_proposals(config)) == 2

    asyncio.run(verify())
