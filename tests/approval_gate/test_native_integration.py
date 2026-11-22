"""End-to-end gate check against a disposable native Basic Memory store."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from approval_gate import ProposalError, cli
from approval_gate.config import Config
from approval_gate.proposals import list_proposals

DURABLE = (
    "---\ntitle: Gated decision\nkind: durable\nstatus: active\nsource: integration check\n---\n\nKeep SQLite local.\n"
)


@pytest.fixture
def proxy(store, tmp_path):
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
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "approval_gate.proxy", "--config", str(config_path)],
        cwd=Path(__file__).resolve().parents[2],
        env={"PYTHONPATH": os.environ.get("PYTHONPATH", "")},
    )
    return root, config, parameters


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
