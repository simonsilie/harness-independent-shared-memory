import asyncio
import json
import os
import signal
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any

import pytest

from shared_memory.approval_gate import ProposalError, cli, proxy
from shared_memory.approval_gate import native as native_transport
from shared_memory.approval_gate.config import Config
from shared_memory.approval_gate.proposals import (
    audit,
    create_or_reuse,
    expired,
    list_proposals,
    load_proposal,
    prepare,
    save_proposal,
)
from shared_memory.approval_gate.writes import (
    NativeCall,
    ProjectListing,
    effective_metadata,
    pin_durable_target,
    temporary_arguments,
)

DURABLE = "---\ntitle: Decision\nkind: durable\nstatus: active\nsource: session 42\n---\n\nKeep SQLite local.\n"
STAMP = "2000-01-01T00:00:00Z"
PROJECT_ID = "00000000-0000-4000-8000-000000000001"
OTHER_PROJECT_ID = "00000000-0000-4000-8000-000000000002"


LISTING: ProjectListing = {
    "projects": [
        {"name": "personal", "external_id": PROJECT_ID},
        {"name": "alpha", "external_id": OTHER_PROJECT_ID},
    ]
}


async def project_listing(_name, _arguments) -> dict[str, Any]:
    return dict(LISTING)


def temporary_content() -> str:
    return (
        f"---\ntitle: Handover\nkind: temporary\nstatus: active\nlast_activity: '{STAMP}'\n---\n\nResume this work.\n"
    )


def make_config(tmp_path: Path, native_command: list[str]) -> Config:
    config = Config(
        native_command=native_command,
        proposals_dir=tmp_path / "approvals",
        audit_log=tmp_path / "audit.jsonl",
        ttl_hours=24,
    )
    prepare(config)
    return config


FAKE_NATIVE = r"""
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

log = open(sys.argv[1], "a")
mode = os.getenv("APPROVAL_GATE_FAKE_MODE")
if mode == "approval_env":
    keys = (
        "UNRELATED_CLIENT_SETTING",
        "BASIC_MEMORY_AUTO_UPDATE",
        "BASIC_MEMORY_CONFIG_DIR",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER",
        "BASIC_MEMORY_DEFAULT_SEARCH_TYPE",
        "BASIC_MEMORY_FORCE_LOCAL",
        "TMPDIR",
    )
    log.write(json.dumps({"env": {key: os.getenv(key) for key in keys}}) + "\n")
if mode == "proxy_shutdown":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
target = None
projects = [{
    "name": "personal",
    "external_id": sys.argv[2],
    "source": "local",
    "local_path": str(Path(sys.argv[1]).parent),
}]
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    log.write(json.dumps({"method": method, "id": message.get("id")}) + "\n")
    if method == "tools/call":
        params = message.get("params", {})
        log.write(json.dumps({"call": params.get("name"), "arguments": params.get("arguments")}) + "\n")
        result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
        if params.get("name") == "bm_project":
            result["structuredContent"] = {"result": {"projects": projects}}
        if params.get("name") == "bm_read":
            result = {"content": [{"type": "text", "text": "Handover lookup failed"}], "isError": True}
        if params.get("name") == "bm_write" and mode == "unknown":
            result = {
                "content": [{"type": "text", "text": json.dumps({
                    "error": "OUTCOME_UNKNOWN", "message": "The write may have happened."
                })}],
                "isError": True,
            }
        elif params.get("name") == "bm_write":
            arguments = params["arguments"]
            content = arguments["content"].encode()
            target = Path(projects[0]["local_path"]) / arguments["identifier"]
            result["structuredContent"] = {"result": {
                "file_path": arguments["identifier"],
                "checksum": hashlib.sha256(content).hexdigest(),
            }}
            blocked_path = os.getenv("APPROVAL_GATE_FAKE_BLOCK_PATH")
            if blocked_path:
                Path(blocked_path).unlink()
                Path(blocked_path).mkdir()
    elif method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "fake", "version": "1"}}
    else:
        result = {}
    log.flush()
    if mode == "exit" and message.get("params", {}).get("name") == "bm_write":
        sys.exit(0)
    if mode in (method, message.get("params", {}).get("name")) and mode is not None:
        continue
    if "id" in message:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
        sys.stdout.flush()
if mode == "proxy_shutdown":
    time.sleep(60)
if target is not None:
    if mode == "shutdown":
        time.sleep(60)
    time.sleep(0.05)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"previous revision" if mode == "stale" else content)
"""


@pytest.fixture
def native(tmp_path):
    script = tmp_path / "fake_native.py"
    script.write_text(FAKE_NATIVE)
    log = tmp_path / "native.log"
    log.write_text("")
    return [sys.executable, str(script), str(log), PROJECT_ID], log


def test_integration_temporary_requires_metadata_and_safe_target(tmp_path):
    listing: ProjectListing = {
        "projects": [{"name": "personal", "external_id": PROJECT_ID, "source": "local", "local_path": str(tmp_path)}]
    }

    async def call_native(_name, _arguments) -> dict[str, Any]:
        return dict(listing)

    args = {"content": temporary_content(), "identifier": "temporary/handover.md", "project": "personal"}
    assert asyncio.run(temporary_arguments(args, listing, call_native))
    assert asyncio.run(temporary_arguments(args | {"identifier": "personal/handovers/note.md"}, listing, call_native))
    assert asyncio.run(
        temporary_arguments(
            args | {"identifier": None, "directory": "temporary", "title": "Note"}, listing, call_native
        )
    )
    for overrides in (
        {"content": DURABLE},
        {"metadata": '{"kind":"durable"}'},
        {"content": temporary_content().replace("status: active", "status: archived")},
        {"content": temporary_content().replace(STAMP, "not-a-date")},
    ):
        assert asyncio.run(temporary_arguments(args | overrides, listing, call_native)) is None
    for target in (
        "durable/temporary/../../durable/decision.md",
        "temporary/../durable/decision.md",
        "/example/temporary/decision.md",
        "durable/x.md",
        "temporary\\handover.md",
        "..",
    ):
        assert asyncio.run(temporary_arguments(args | {"identifier": target}, listing, call_native)) is None, target


RESOLVABLE_TARGETS = [
    ("Team Personal", "temporary/note.md"),
    ("team-personal", "temporary/note.md"),
    (PROJECT_ID, "temporary/note.md"),
    ("personal", "team-personal/temporary/note.md"),
]
UNRESOLVABLE_TARGETS = [
    ("personal", "alpha/temporary/note.md"),
    ("missing", "temporary/note.md"),
]


@pytest.fixture
def listing(tmp_path: Path) -> ProjectListing:
    return {
        "projects": [
            {
                "name": "personal",
                "qualified_name": "Team Personal",
                "external_id": PROJECT_ID,
                "source": "local",
                "local_path": str(tmp_path),
            },
            {"name": "alpha", "external_id": OTHER_PROJECT_ID, "source": "local", "local_path": str(tmp_path)},
        ]
    }


@pytest.fixture
def call_native(listing: ProjectListing) -> NativeCall:
    async def call(_name, _arguments) -> dict[str, Any]:
        return dict(listing)

    return call


@pytest.mark.parametrize(("project", "identifier"), RESOLVABLE_TARGETS)
def test_temporary_write_resolves_project(
    listing: ProjectListing, call_native: NativeCall, project: str, identifier: str
) -> None:
    sut = temporary_arguments
    args = {"content": temporary_content(), "identifier": identifier, "project": project}

    forwarded = asyncio.run(sut(args, listing, call_native))

    assert forwarded is not None and forwarded["project"] == PROJECT_ID


@pytest.mark.parametrize(("project", "identifier"), UNRESOLVABLE_TARGETS)
def test_temporary_write_with_unresolvable_project_needs_approval(
    listing: ProjectListing, call_native: NativeCall, project: str, identifier: str
) -> None:
    sut = temporary_arguments
    args = {"content": temporary_content(), "identifier": identifier, "project": project}

    forwarded = asyncio.run(sut(args, listing, call_native))

    assert forwarded is None


@pytest.mark.parametrize(("project", "identifier"), RESOLVABLE_TARGETS)
def test_durable_write_resolves_project(listing: ProjectListing, project: str, identifier: str) -> None:
    sut = pin_durable_target
    args = {"content": DURABLE, "identifier": identifier, "project": project}

    _, pinned = sut(args, listing)

    assert pinned["project"] == PROJECT_ID


@pytest.mark.parametrize(("project", "identifier"), UNRESOLVABLE_TARGETS)
def test_durable_write_refuses_unresolvable_project(listing: ProjectListing, project: str, identifier: str) -> None:
    sut = pin_durable_target
    args = {"content": DURABLE, "identifier": identifier, "project": project}

    with pytest.raises(ProposalError):
        sut(args, listing)


def test_constrained_session_blocks_temporary_writes(listing: ProjectListing, call_native: NativeCall) -> None:
    sut = temporary_arguments
    listing["constrained_project"] = "personal"
    args = {"content": temporary_content(), "identifier": "temporary/note.md", "project": "personal"}

    forwarded = asyncio.run(sut(args, listing, call_native))

    assert forwarded is None


def test_malformed_native_listing_is_a_visible_tool_error(
    tmp_path: Path, listing: ProjectListing, call_native: NativeCall
) -> None:
    sut = proxy.handle_write
    del listing["projects"][0]["external_id"]  # type: ignore[unsupported-delete]
    config = make_config(tmp_path, ["unused"])
    arguments = {"content": temporary_content(), "identifier": "temporary/note.md", "project": "personal"}
    request = {"id": 1, "params": {"name": "bm_write", "arguments": arguments}}

    response = asyncio.run(sut(request, config, tmp_path / "config.json", call_native))

    assert response.message["result"]["isError"]


def test_malformed_frontmatter_is_reported():
    with pytest.raises(ProposalError, match="Malformed note frontmatter"):
        effective_metadata({"content": "---\ntitle: [unclosed\n---\nbody"})


def test_integration_explicit_project_required_for_durable(tmp_path, native):
    config = make_config(tmp_path, native[0])
    with pytest.raises(ProposalError, match="explicit project"):
        create_or_reuse(config, {"content": DURABLE, "identifier": "decision.md"}, LISTING)


def test_integration_dedupe_matches_the_exact_write(tmp_path, native):
    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    first, created = create_or_reuse(config, args, LISTING)
    second, reused = create_or_reuse(config, args, LISTING)
    assert created and not reused
    assert first["id"] == second["id"]
    for change in (
        {"identifier": "other.md"},
        {"project": "alpha"},
        {"metadata": {"tag": "other"}},
        {"expected_checksum": "another revision"},
    ):
        distinct, created = create_or_reuse(config, args | change, LISTING)
        assert created and distinct["id"] != first["id"]
    assert first["source"] == "session 42"
    assert first["content_hash"]


def test_integration_concurrent_identical_writes_share_one_proposal(tmp_path, native):
    import threading

    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    ids = []
    errors = []

    def create():
        try:
            ids.append(create_or_reuse(config, args, LISTING)[0]["id"])
        except Exception as error:  # noqa: BLE001 - collected for assertion
            errors.append(error)

    threads = [threading.Thread(target=create) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(set(ids)) == 1


def test_integration_expired_proposals_are_not_reused(tmp_path, native):
    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    proposal, _ = create_or_reuse(config, args, LISTING, now=now)
    deadline = now + timedelta(hours=config.ttl_hours)

    fresh, created = create_or_reuse(config, args, LISTING, now=deadline)

    assert expired(proposal, now=deadline)
    assert created and fresh["id"] != proposal["id"]


def test_invalid_expiry_is_reported():
    with pytest.raises(ProposalError, match="invalid expiry"):
        expired({"id": "broken"})


def test_integration_audit_log_is_jsonl(tmp_path, native):
    config = make_config(tmp_path, native[0])
    audit(config, "first", proposal_id="a")
    audit(config, "second", proposal_id="b")
    records = [json.loads(line) for line in config.audit_log.read_text().splitlines()]
    assert [record["event"] for record in records] == ["first", "second"]
    assert all(record["timestamp"].endswith("Z") for record in records)


def test_integration_prepare_enforces_private_permissions(tmp_path, native):
    config = make_config(tmp_path, native[0])
    config.proposals_dir.chmod(0o755)
    config.audit_log.write_text("")
    config.audit_log.chmod(0o644)
    parent_mode = stat.S_IMODE(config.audit_log.parent.stat().st_mode)

    prepare(config)

    assert config.proposals_dir.stat().st_mode & 0o777 == 0o700
    assert config.audit_log.stat().st_mode & 0o777 == 0o600
    assert stat.S_IMODE(config.audit_log.parent.stat().st_mode) == parent_mode


def test_integration_audit_preserves_working_directory_permissions(tmp_path, native, monkeypatch):
    working_directory = tmp_path / "workspace"
    working_directory.mkdir()
    working_directory.chmod(0o750)
    monkeypatch.chdir(working_directory)
    config = Config(native_command=native[0], proposals_dir=Path("proposals"), audit_log=Path("audit.jsonl"))

    prepare(config)
    audit(config, "first")

    assert stat.S_IMODE(working_directory.stat().st_mode) == 0o750
    assert stat.S_IMODE(config.proposals_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(config.audit_log.stat().st_mode) == 0o600


async def empty_reply(_name, _arguments):
    return {}


def test_integration_malformed_write_is_a_visible_tool_error(tmp_path, native):
    config = make_config(tmp_path, native[0])
    request = {"id": 1, "params": {"arguments": {"content": DURABLE, "identifier": "decision.md"}}}
    response = asyncio.run(proxy.handle_write(request, config, tmp_path / "config.json", empty_reply))
    assert response.message["result"]["isError"]
    assert [json.loads(line)["event"] for line in config.audit_log.read_text().splitlines()] == ["write_refused"]


def test_integration_write_notification_returns_visible_proposal_id(tmp_path, native):
    config = make_config(tmp_path, native[0])
    response = asyncio.run(
        proxy.handle_write(
            {"params": {"arguments": {"content": DURABLE, "project": "personal"}}},
            config,
            tmp_path / "config.json",
            project_listing,
        )
    )
    assert response.message["result"]["isError"]
    assert "Proposal" in response.message["result"]["content"][0]["text"]


def read_reply(replies, expected_id):
    while True:
        line = replies.get(timeout=25)
        assert line, "proxy closed before replying"
        reply = json.loads(line)
        if reply.get("id") == expected_id:
            return reply


def test_integration_proxy_gates_writes_and_allows_only_supported_tools(tmp_path, native):
    native_command, log = native
    config = make_config(tmp_path, native_command)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "native_command": native_command,
                "proposals_dir": config.proposals_dir.name,
                "audit_log": config.audit_log.name,
                "ttl_hours": 24,
            }
        )
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "shared_memory.approval_gate.proxy", "--config", str(config_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=Path(__file__).resolve().parents[3],
    )
    assert process.stdin is not None and process.stdout is not None
    replies: Queue[str] = Queue()

    def receive():
        assert process.stdout is not None
        for line in process.stdout:
            replies.put(line)
        replies.put("")

    Thread(target=receive, daemon=True).start()
    try:

        def send(message):
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert "result" in read_reply(replies, 1)

        durable_args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "bm_write", "arguments": durable_args},
            }
        )
        reply = read_reply(replies, 2)
        assert not reply["result"]["isError"]
        assert "shared_memory.approval_gate.cli" in reply["result"]["content"][0]["text"]

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "bm_search", "arguments": {}}})
        assert "result" in read_reply(replies, 3)

        edit = {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "bm_edit", "arguments": {}}}
        send(edit)
        assert read_reply(replies, 10)["result"]["isError"]
        send(
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {"name": "bm_project", "arguments": {"command": "create"}},
            }
        )
        assert read_reply(replies, 11)["result"]["isError"]

        temporary_args = {"content": temporary_content(), "project": "personal", "identifier": "temporary/handover.md"}
        send(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "bm_write", "arguments": temporary_args},
            }
        )
        assert "result" in read_reply(replies, 4)

        batched_write = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "bm_write", "arguments": durable_args},
        }
        legit = {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "bm_search", "arguments": {}}}
        send([batched_write, edit | {"id": 12}, legit])
        assert read_reply(replies, 5)["result"]["isError"]
        assert read_reply(replies, 12)["result"]["isError"]
        assert "result" in read_reply(replies, 6)

        send(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "bm_write", "arguments": temporary_args | {"expected_checksum": "revision"}},
            }
        )
        failure = read_reply(replies, 7)["result"]
        assert failure["isError"]
        assert "Handover lookup failed" in failure["content"][0]["text"]

        config.audit_log.unlink()
        config.audit_log.mkdir()
        send(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "bm_write", "arguments": durable_args | {"identifier": "another.md"}},
            }
        )
        failure = read_reply(replies, 8)["result"]
        assert failure["isError"]
        assert config.audit_log.name in failure["content"][0]["text"]

        send({"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "bm_search", "arguments": {}}})
        assert not read_reply(replies, 9)["result"]["isError"]
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert not any(entry.get("call") == "bm_edit" for entry in calls)
    assert all(entry["arguments"]["command"] == "list" for entry in calls if entry.get("call") == "bm_project")
    written = [entry["arguments"] for entry in calls if "call" in entry and entry["call"] == "bm_write"]
    assert written == [temporary_args | {"project": PROJECT_ID, "overwrite": False}]
    (proposal,) = list_proposals(config)
    assert proposal["arguments"]["identifier"] == "decision.md"


def test_integration_pending_write_does_not_hold_up_later_messages(tmp_path, native):
    native_command, log = native
    config = make_config(tmp_path, native_command)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "native_command": native_command,
                "proposals_dir": config.proposals_dir.name,
                "audit_log": config.audit_log.name,
                "env": {"APPROVAL_GATE_FAKE_MODE": "bm_project"},
            }
        )
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "shared_memory.approval_gate.proxy", "--config", str(config_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=Path(__file__).resolve().parents[3],
    )
    assert process.stdin is not None and process.stdout is not None
    replies: Queue[str] = Queue()
    Thread(target=lambda: [*map(replies.put, process.stdout), replies.put("")], daemon=True).start()
    temporary_args = {
        "content": temporary_content(),
        "project": "personal",
        "identifier": "temporary/handover.md",
        "expected_checksum": "revision",
    }
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "bm_write", "arguments": temporary_args},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "bm_search", "arguments": {}}},
    ]
    try:
        for message in messages:
            process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

        first = json.loads(replies.get(timeout=10))
    finally:
        process.kill()
        process.wait(timeout=5)

    assert first["id"] == 2 and not first["result"]["isError"]


@pytest.mark.parametrize("mode", ["normal", "proxy_shutdown", "bm_project"])
def test_integration_proxy_shutdown_on_client_eof(tmp_path, native, mode):
    config = make_config(tmp_path, native[0]).model_copy(update={"env": {"APPROVAL_GATE_FAKE_MODE": mode}})
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    identifier = "temporary/handover.md"
    content = temporary_content()
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "bm_write",
            "arguments": {"content": content, "identifier": identifier, "project": "personal"},
        },
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from shared_memory.approval_gate import native, proxy; "
            "native.SHUTDOWN_TIMEOUT = 1; raise SystemExit(proxy.main())",
            "--config",
            str(config_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(json.dumps(request) + "\n", timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=5)
        raise

    if mode == "bm_project":
        assert process.returncode != 0
        assert not stdout
        assert "Timed out draining pending writes" in stderr
        return

    assert not json.loads(stdout)["result"]["isError"]
    if mode == "normal":
        assert process.returncode == 0
        assert (tmp_path / identifier).read_text() == content
    else:
        assert process.returncode != 0
        assert "timed out during graceful shutdown" in stderr


@pytest.mark.parametrize(
    ("content", "identifier"), [(DURABLE, "decision.md"), (temporary_content(), "temporary/handover.md")]
)
def test_integration_write_lists_projects_once(tmp_path, native, content, identifier):
    config = make_config(tmp_path, native[0])
    calls = []

    async def call_native(name, arguments):
        calls.append(name)
        return {
            "projects": [
                {"name": "personal", "external_id": PROJECT_ID, "source": "local", "local_path": str(tmp_path)}
            ]
        }

    arguments = {"content": content, "project": "personal", "identifier": identifier}
    request = {"id": 1, "params": {"arguments": arguments}}

    asyncio.run(proxy.handle_write(request, config, tmp_path / "config.json", call_native))

    assert calls == ["bm_project"]


def test_integration_approval_reports_a_failed_final_save(tmp_path, native):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal, _ = create_or_reuse(config, arguments, LISTING)
    blocked = config.proposals_dir / f"{proposal['id']}.json"
    config = config.model_copy(update={"env": {"APPROVAL_GATE_FAKE_BLOCK_PATH": str(blocked)}})

    with pytest.raises(ProposalError, match="note was written.*stays applying"):
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    assert (tmp_path / "decision.md").read_text() == DURABLE
    events = [json.loads(line)["event"] for line in config.audit_log.read_text().splitlines()]
    assert events[-1] == "proposal_applying"


def test_integration_owner_cli_approves_exact_arguments_through_native(tmp_path, native, monkeypatch):
    native_command, log = native
    monkeypatch.setenv("UNRELATED_CLIENT_SETTING", "synthetic-value")
    monkeypatch.setenv("BASIC_MEMORY_AUTO_UPDATE", "true")
    monkeypatch.setenv("BASIC_MEMORY_CONFIG_DIR", str(tmp_path / "inherited"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    config = make_config(tmp_path, native_command).model_copy(
        update={
            "env": {
                "APPROVAL_GATE_FAKE_MODE": "approval_env",
                "BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "configured"),
                "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "openai",
                "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "text",
                "BASIC_MEMORY_FORCE_LOCAL": "false",
            }
        }
    )
    arguments = {
        "content": DURABLE,
        "project": "personal",
        "identifier": "personal/decisions/decision",
        "expected_checksum": "sha256:abc",
    }
    proposal, _ = create_or_reuse(config, arguments, LISTING)

    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0

    stored = load_proposal(config, proposal["id"])
    assert stored["status"] == "approved" and stored["approved_at"]
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0]["env"] == {
        "UNRELATED_CLIENT_SETTING": None,
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "configured"),
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "fastembed",
        "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "hybrid",
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "TMPDIR": str(tmp_path),
    }
    written = [entry["arguments"] for entry in calls if "call" in entry and entry["call"] == "bm_write"]
    assert written == [
        arguments | {"project": PROJECT_ID, "identifier": "decisions/decision.md", "output_format": "json"}
    ]
    assert (tmp_path / "decisions/decision.md").read_text() == DURABLE
    events = [json.loads(line)["event"] for line in config.audit_log.read_text().splitlines()]
    assert "proposal_created" in events and "proposal_approved" in events


def test_integration_approval_can_be_retried_after_audit_failure(tmp_path, native):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal, _ = create_or_reuse(config, arguments, LISTING)
    saved_audit = config.audit_log.rename(tmp_path / "saved-audit.jsonl")
    config.audit_log.mkdir()

    with pytest.raises(ProposalError, match="Could not record approval") as failure:
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    assert isinstance(failure.value.__cause__, IsADirectoryError)
    assert load_proposal(config, proposal["id"])["status"] == "pending"
    assert not (tmp_path / "decision.md").exists()

    config.audit_log.rmdir()
    saved_audit.rename(config.audit_log)

    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0
    assert load_proposal(config, proposal["id"])["status"] == "approved"
    assert (tmp_path / "decision.md").read_text() == DURABLE


def test_integration_approval_succeeds_when_final_audit_append_fails(tmp_path, native):
    config = make_config(tmp_path, native[0])
    config = config.model_copy(update={"env": {"APPROVAL_GATE_FAKE_BLOCK_PATH": str(config.audit_log)}})
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal, _ = create_or_reuse(config, arguments, LISTING)

    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0

    assert config.audit_log.is_dir()
    assert load_proposal(config, proposal["id"])["status"] == "approved"
    assert (tmp_path / "decision.md").read_text() == DURABLE


@pytest.mark.parametrize(
    ("mode", "expected_status", "expected_error"),
    [
        ("bm_project", "pending", "bm_project timed out"),
        ("bm_write", "outcome_unknown", "bm_write timed out"),
        ("unknown", "outcome_unknown", "Check the native store.*OUTCOME_UNKNOWN"),
        ("exit", "outcome_unknown", "Check the native store.*closed before replying"),
        ("shutdown", "outcome_unknown", "timed out during graceful shutdown"),
        ("stale", "outcome_unknown", "does not match the accepted revision"),
    ],
)
def test_integration_native_approval_failure(tmp_path, native, monkeypatch, mode, expected_status, expected_error):
    config = make_config(tmp_path, native[0]).model_copy(update={"env": {"APPROVAL_GATE_FAKE_MODE": mode}})
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal, _ = create_or_reuse(config, arguments, LISTING)
    monkeypatch.setattr(native_transport, "REQUEST_TIMEOUT", 1)
    monkeypatch.setattr(native_transport, "SHUTDOWN_TIMEOUT", 1)

    with pytest.raises(ProposalError, match=expected_error):
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    stored = load_proposal(config, proposal["id"])
    assert stored["status"] == expected_status
    assert (tmp_path / "decision.md").exists() is (mode in {"bm_write", "stale"})


def test_integration_approval_preserves_native_error_when_audit_fails(tmp_path, native, monkeypatch):
    config = make_config(tmp_path, native[0])
    config = config.model_copy(
        update={"env": {"APPROVAL_GATE_FAKE_MODE": "bm_write", "APPROVAL_GATE_FAKE_BLOCK_PATH": str(config.audit_log)}}
    )
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal, _ = create_or_reuse(config, arguments, LISTING)
    monkeypatch.setattr(native_transport, "REQUEST_TIMEOUT", 1)

    with pytest.raises(ProposalError, match="Check the native store.*Native bm_write timed out") as failure:
        cli.command_approve(config, proposal["id"], confirm=lambda _: True)

    assert "Could not finish recording the failure" in str(failure.value)
    assert "outcome_unknown" in str(failure.value)
    assert isinstance(failure.value.__cause__, ProposalError)
    assert load_proposal(config, proposal["id"])["status"] == "outcome_unknown"
    assert (tmp_path / "decision.md").read_text() == DURABLE


def test_integration_legacy_proposal_without_pinned_project_requires_resubmission(tmp_path, native):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    legacy, _ = create_or_reuse(config, arguments, LISTING)
    del legacy["project_external_id"]
    legacy["arguments"]["project"] = "personal"
    save_proposal(config, legacy)

    with pytest.raises(ProposalError, match="no pinned project UUID"):
        cli.command_approve(config, legacy["id"], confirm=lambda _: True)

    proposal, created = create_or_reuse(config, arguments, LISTING)
    assert created and proposal["id"] != legacy["id"]
    assert proposal["arguments"]["project"] == PROJECT_ID


def test_integration_owner_cli_rejects_and_keeps_proposal(tmp_path, native):
    config = make_config(tmp_path, native[0])
    proposal, _ = create_or_reuse(config, {"content": DURABLE, "project": "personal"}, LISTING)
    assert cli.command_reject(config, proposal["id"]) == 0
    assert load_proposal(config, proposal["id"])["status"] == "rejected"
    with pytest.raises(ProposalError, match="already rejected"):
        cli.command_approve(config, proposal["id"])


@pytest.mark.parametrize("change", ["reject", "expire", "approve"])
def test_integration_owner_cli_rechecks_proposal_after_confirmation(tmp_path, native, change):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal_id = create_or_reuse(config, arguments, LISTING)[0]["id"]

    def confirm(_prompt):
        if change == "reject":
            cli.command_reject(config, proposal_id)
        elif change == "expire":
            proposal = load_proposal(config, proposal_id)
            proposal["expires_at"] = "2026-01-01T00:00:00Z"
            save_proposal(config, proposal)
        else:
            assert cli.command_approve(config, proposal_id, confirm=lambda _: True) == 0
        return True

    with pytest.raises(ProposalError, match={"reject": "rejected", "expire": "expired", "approve": "approved"}[change]):
        cli.command_approve(config, proposal_id, confirm=confirm)

    calls = [json.loads(line) for line in native[1].read_text().splitlines()]
    assert sum(entry.get("call") == "bm_write" for entry in calls) == int(change == "approve")


def test_integration_approval_requires_a_terminal(tmp_path, native, capsys, monkeypatch):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "other.md", "expected_checksum": "revision"}
    proposal_id = create_or_reuse(config, arguments, LISTING)[0]["id"]
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(ProposalError, match="interactive terminal"):
        cli.command_approve(config, proposal_id)

    preview = capsys.readouterr().out
    assert '"identifier": "other.md"' in preview
    assert '"expected_checksum": "revision"' in preview
    assert native[1].read_text() == ""


def test_integration_proposal_refuses_unconditional_overwrite(tmp_path, native):
    config = make_config(tmp_path, native[0])
    with pytest.raises(ProposalError, match="expected_checksum"):
        create_or_reuse(config, {"content": DURABLE, "project": "personal", "overwrite": True}, LISTING)
