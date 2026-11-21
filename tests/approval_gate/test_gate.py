import json
import subprocess
import sys
from pathlib import Path
from queue import Queue
from threading import Thread

import pytest

from approval_gate import ProposalError, cli, proxy
from approval_gate.config import Config
from approval_gate.proposals import (
    audit,
    create_or_reuse,
    expired,
    load_proposal,
    prepare,
    save_proposal,
)
from approval_gate.writes import effective_metadata, temporary_arguments

DURABLE = "---\ntitle: Decision\nkind: durable\nstatus: active\nsource: session 42\n---\n\nKeep SQLite local.\n"
STAMP = "2000-01-01T00:00:00Z"
PROJECT_ID = "00000000-0000-4000-8000-000000000001"


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
import json
import sys
from pathlib import Path

log = open(sys.argv[1], "a")
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
    elif method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "fake", "version": "1"}}
    else:
        result = {}
    log.flush()
    if "id" in message:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
        sys.stdout.flush()
"""


@pytest.fixture
def native(tmp_path):
    script = tmp_path / "fake_native.py"
    script.write_text(FAKE_NATIVE)
    log = tmp_path / "native.log"
    log.write_text("")
    return [sys.executable, str(script), str(log), PROJECT_ID], log


def test_temporary_requires_metadata_and_safe_target(tmp_path):
    def call_native(_name, _arguments):
        return {
            "projects": [
                {"name": "personal", "external_id": PROJECT_ID, "source": "local", "local_path": str(tmp_path)}
            ]
        }

    args = {"content": temporary_content(), "identifier": "temporary/handover.md", "project": "personal"}
    assert temporary_arguments(args, call_native)
    assert temporary_arguments(args | {"identifier": "personal/handovers/note.md"}, call_native)
    assert temporary_arguments(args | {"identifier": None, "directory": "temporary", "title": "Note"}, call_native)
    for overrides in (
        {"content": DURABLE},
        {"metadata": '{"kind":"durable"}'},
        {"content": temporary_content().replace("status: active", "status: archived")},
        {"content": temporary_content().replace(STAMP, "not-a-date")},
    ):
        assert temporary_arguments(args | overrides, call_native) is None
    for target in (
        "durable/temporary/../../durable/decision.md",
        "temporary/../durable/decision.md",
        "/example/temporary/decision.md",
        "durable/x.md",
        "temporary\\handover.md",
        "..",
    ):
        assert temporary_arguments(args | {"identifier": target}, call_native) is None, target


def test_malformed_frontmatter_is_reported():
    with pytest.raises(ProposalError, match="Malformed note frontmatter"):
        effective_metadata({"content": "---\ntitle: [unclosed\n---\nbody"})


def test_explicit_project_required_for_durable(tmp_path, native):
    config = make_config(tmp_path, native[0])
    with pytest.raises(ProposalError, match="explicit project"):
        create_or_reuse(config, {"content": DURABLE, "identifier": "decision.md"})


def test_dedupe_matches_the_exact_write(tmp_path, native):
    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    first, created = create_or_reuse(config, args)
    second, reused = create_or_reuse(config, args)
    assert created and not reused
    assert first["id"] == second["id"]
    for change in (
        {"identifier": "other.md"},
        {"project": "alpha"},
        {"metadata": {"tag": "other"}},
        {"expected_checksum": "another revision"},
    ):
        distinct, created = create_or_reuse(config, args | change)
        assert created and distinct["id"] != first["id"]
    assert first["source"] == "session 42"
    assert first["content_hash"]


def test_concurrent_identical_writes_share_one_proposal(tmp_path, native):
    import threading

    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    ids = []
    errors = []

    def create():
        try:
            ids.append(create_or_reuse(config, args)[0]["id"])
        except Exception as error:  # noqa: BLE001 - collected for assertion
            errors.append(error)

    threads = [threading.Thread(target=create) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(set(ids)) == 1


def test_expired_proposals_are_not_reused(tmp_path, native):
    config = make_config(tmp_path, native[0])
    args = {"content": DURABLE, "project": "personal"}
    proposal, _ = create_or_reuse(config, args)
    proposal["expires_at"] = "2026-01-01T00:00:00Z"
    save_proposal(config, proposal)

    assert expired(proposal)
    fresh, created = create_or_reuse(config, args)
    assert created and fresh["id"] != proposal["id"]


def test_invalid_expiry_is_reported():
    with pytest.raises(ProposalError, match="invalid expiry"):
        expired({"id": "broken"})


def test_audit_log_is_jsonl(tmp_path, native):
    config = make_config(tmp_path, native[0])
    audit(config, "first", proposal_id="a")
    audit(config, "second", proposal_id="b")
    records = [json.loads(line) for line in config.audit_log.read_text().splitlines()]
    assert [record["event"] for record in records] == ["first", "second"]
    assert all(record["timestamp"].endswith("Z") for record in records)


def test_prepare_enforces_private_permissions(tmp_path, native):
    config = make_config(tmp_path, native[0])
    config.proposals_dir.chmod(0o755)
    config.audit_log.write_text("")
    config.audit_log.chmod(0o644)
    prepare(config)
    assert config.proposals_dir.stat().st_mode & 0o777 == 0o700
    assert config.audit_log.stat().st_mode & 0o777 == 0o600


def test_malformed_write_is_a_visible_tool_error(tmp_path, native):
    config = make_config(tmp_path, native[0])
    request = {"id": 1, "params": {"arguments": {"content": DURABLE, "identifier": "decision.md"}}}
    response = proxy.handle_write(request, config, tmp_path / "config.json", lambda *_: {})
    assert response["result"]["isError"]
    assert [json.loads(line)["event"] for line in config.audit_log.read_text().splitlines()] == ["write_refused"]


def test_write_notification_returns_visible_proposal_id(tmp_path, native):
    config = make_config(tmp_path, native[0])
    response = proxy.handle_write(
        {"params": {"arguments": {"content": DURABLE, "project": "p"}}}, config, tmp_path / "config.json", lambda *_: {}
    )
    assert response["result"]["isError"]
    assert "Proposal" in response["result"]["content"][0]["text"]


def read_reply(replies, expected_id):
    while True:
        line = replies.get(timeout=25)
        assert line, "proxy closed before replying"
        reply = json.loads(line)
        if reply.get("id") == expected_id:
            return reply


def test_integration_proxy_gates_durable_writes_and_forwards_everything_else(tmp_path, native):
    native_command, log = native
    config = make_config(tmp_path, native_command)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "native_command": native_command,
                "proposals_dir": str(config.proposals_dir),
                "audit_log": str(config.audit_log),
                "ttl_hours": 24,
            }
        )
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "approval_gate.proxy", "--config", str(config_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=Path(__file__).resolve().parents[2],
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
        assert "approval_gate.cli" in reply["result"]["content"][0]["text"]

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "bm_search", "arguments": {}}})
        assert "result" in read_reply(replies, 3)

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
        process.stdin.write(json.dumps([batched_write, legit]) + "\n")
        process.stdin.flush()
        assert read_reply(replies, 5)["result"]["isError"]
        assert "result" in read_reply(replies, 6)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    calls = [json.loads(line) for line in log.read_text().splitlines()]
    written = [entry["arguments"] for entry in calls if "call" in entry and entry["call"] == "bm_write"]
    assert written == [temporary_args | {"project": PROJECT_ID, "overwrite": False}]


def test_owner_cli_approves_exact_arguments_through_native(tmp_path, native):
    native_command, log = native
    config = make_config(tmp_path, native_command)
    arguments = {
        "content": DURABLE,
        "project": "personal",
        "identifier": "decision.md",
        "expected_checksum": "sha256:abc",
    }
    proposal, _ = create_or_reuse(config, arguments)

    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0

    stored = load_proposal(config, proposal["id"])
    assert stored["status"] == "approved" and stored["approved_at"]
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    written = [entry["arguments"] for entry in calls if "call" in entry and entry["call"] == "bm_write"]
    assert written == [arguments]
    events = [json.loads(line)["event"] for line in config.audit_log.read_text().splitlines()]
    assert "proposal_created" in events and "proposal_approved" in events


def test_owner_cli_rejects_and_keeps_proposal(tmp_path, native):
    config = make_config(tmp_path, native[0])
    proposal, _ = create_or_reuse(config, {"content": DURABLE, "project": "personal"})
    assert cli.command_reject(config, proposal["id"]) == 0
    assert load_proposal(config, proposal["id"])["status"] == "rejected"
    with pytest.raises(ProposalError, match="already rejected"):
        cli.command_approve(config, proposal["id"])


@pytest.mark.parametrize("change", ["reject", "expire", "approve"])
def test_owner_cli_rechecks_proposal_after_confirmation(tmp_path, native, change):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "decision.md"}
    proposal_id = create_or_reuse(config, arguments)[0]["id"]

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


def test_approval_requires_a_terminal(tmp_path, native, capsys, monkeypatch):
    config = make_config(tmp_path, native[0])
    arguments = {"content": DURABLE, "project": "personal", "identifier": "other.md", "expected_checksum": "revision"}
    proposal_id = create_or_reuse(config, arguments)[0]["id"]
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(ProposalError, match="interactive terminal"):
        cli.command_approve(config, proposal_id)

    preview = capsys.readouterr().out
    assert '"identifier": "other.md"' in preview
    assert '"expected_checksum": "revision"' in preview
    assert native[1].read_text() == ""


def test_proposal_refuses_unconditional_overwrite(tmp_path, native):
    config = make_config(tmp_path, native[0])
    with pytest.raises(ProposalError, match="expected_checksum"):
        create_or_reuse(config, {"content": DURABLE, "project": "personal", "overwrite": True})
