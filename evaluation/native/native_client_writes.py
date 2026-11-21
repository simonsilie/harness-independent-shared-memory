import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-native-writes")
OUT.mkdir(parents=True)
logger.info(f"Native client write artifacts: {OUT}")
state, corpus, workspace = (OUT / name for name in ("state", "corpus", "workspace"))
for directory in (state, corpus, workspace):
    directory.mkdir()
(state / "config.json").write_text(
    json.dumps(
        {
            "projects": {"main": {"path": str(corpus), "mode": "local"}},
            "default_project": "main",
            "database_backend": "sqlite",
            "database_url": None,
        }
    )
    + "\n"
)
before = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "evaluation/corpus").rglob("*.md")
}
env = {k: v for k, v in os.environ.items() if not k.startswith(("BASIC_MEMORY_", "PHASE1B_"))}
env.pop("PYTEST_CURRENT_TEST", None)
env.update(
    {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(corpus),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
        "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "text",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR": str(OUT / "models"),
        "HF_HOME": str(OUT / "models"),
        "HF_HUB_OFFLINE": "1",
        "WATCHFILES_FORCE_POLLING": "true",
    }
)
TOOLS = ["bm_read", "bm_write"]
SERVER = [sys.executable, str(Path(__file__).with_name("mcp_server_guard.py")), "mcp", "--project", "main"]


def dump(name, value):
    (OUT / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n")


def run(client, name, operations):
    prompt = (
        "Use only the configured Basic Memory bm_read and bm_write tools. "
        "This authorizes the following writes to disposable test notes. "
        "Perform these calls in order, exactly once each, with project='main' and output_format='json'. "
        "Do not retry, repair, refresh checksums or use other tools, even after an expected conflict.\n"
        + "\n".join(f"{tool}: {json.dumps(arguments)}" for tool, arguments in operations)
    )
    (OUT / f"{name}-prompt.txt").write_text(prompt)
    server_env = {
        k: v
        for k, v in env.items()
        if k.startswith("BASIC_MEMORY_")
        or k
        in {
            "HF_HOME",
            "HF_HUB_OFFLINE",
            "WATCHFILES_FORCE_POLLING",
        }
    } | {"PHASE1B_GUARD_PATH": str(OUT / f"{name}.guard.json")}
    if client == "codex":
        config = {
            "mcp_servers.basic_memory.command": SERVER[0],
            "mcp_servers.basic_memory.args": SERVER[1:],
            **{f"mcp_servers.basic_memory.env.{key}": value for key, value in server_env.items()},
            "mcp_servers.basic_memory.enabled_tools": TOOLS,
            "mcp_servers.basic_memory.required": True,
            "mcp_servers.basic_memory.default_tools_approval_mode": "approve",
            "log_dir": str(OUT / "logs"),
            "sqlite_home": str(OUT / "codex-state"),
            "project_doc_max_bytes": 0,
            "web_search": "disabled",
            **{
                f"features.{key}": False
                for key in (
                    "shell_tool",
                    "shell_snapshot",
                    "apps",
                    "multi_agent",
                    "multi_agent_v2",
                    "browser_use",
                    "computer_use",
                    "hooks",
                    "memories",
                )
            },
        }
        command = [
            "codex",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-s",
            "read-only",
            "-C",
            str(workspace),
        ]
        for key, value in config.items():
            command.extend(["-c", f"{key}={json.dumps(value)}"])
        result = subprocess.run(command + [prompt], env=env, cwd=workspace, capture_output=True, text=True, timeout=600)
    else:
        config = {
            "mcp": {
                "servers": {
                    "basic_memory": {
                        "type": "local",
                        "command": SERVER,
                        "environment": server_env,
                        "codemode": False,
                        "timeout": {"startup": 120000, "catalog": 30000, "execution": 120000},
                    }
                }
            },
            "agents": {
                "native-writes": {
                    "description": "Disposable native conditional-write check",
                    "mode": "primary",
                    "permissions": [{"action": "*", "resource": "*", "effect": "deny"}]
                    + [{"action": f"basic_memory_{tool}", "resource": "*", "effect": "allow"} for tool in TOOLS],
                    "system": "Use only Basic Memory tools for the requested disposable note operations.",
                }
            },
        }
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        address = f"http://127.0.0.1:{port}"
        client_env = env | {"OPENCODE_CONFIG_CONTENT": json.dumps(config), "OPENCODE_PASSWORD": uuid.uuid4().hex}
        with (OUT / f"{name}-server.log").open("w") as log:
            server = subprocess.Popen(
                ["opencode", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                cwd=ROOT,
                env=client_env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 60
                while True:
                    assert server.poll() is None and time.monotonic() < deadline, "OpenCode did not start"
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=1):
                            break
                    except OSError:
                        time.sleep(0.1)
                command = [
                    "opencode",
                    "--server",
                    address,
                    "run",
                    "--agent",
                    "native-writes",
                    "--model",
                    "opencode-go/glm-5.3-flash",
                    "--format",
                    "json",
                    "--title",
                    name,
                ]
                readiness = subprocess.run(
                    command + ["Reply ready without using tools."],
                    cwd=ROOT,
                    env=client_env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                (OUT / f"{name}-readiness.events.jsonl").write_text(readiness.stdout)
                assert readiness.returncode == 0, readiness.stderr
                connection = subprocess.run(
                    [
                        "opencode",
                        "--server",
                        address,
                        "api",
                        "post",
                        "/api/experimental/mcp/basic_memory/connect?" + urlencode({"location[directory]": str(ROOT)}),
                    ],
                    cwd=ROOT,
                    env=client_env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                (OUT / f"{name}-connection.stdout").write_text(connection.stdout)
                assert connection.returncode == 0, connection.stderr
                result = subprocess.run(
                    command + [prompt],
                    cwd=ROOT,
                    env=client_env,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
            finally:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    # Environment values are deliberately omitted from retained client configuration.
    (OUT / f"{name}.events.jsonl").write_text(result.stdout)
    (OUT / f"{name}.stderr").write_text(result.stderr)
    assert result.returncode == 0, f"{name} exited {result.returncode}"
    calls = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if client == "codex":
            item = event.get("item", {})
            if event.get("type") != "item.completed" or item.get("type") != "mcp_tool_call":
                continue
            assert item["server"] == "basic_memory"
            content = "".join(block.get("text", "") for block in (item.get("result") or {}).get("content", []))
            calls.append((item["tool"], item["arguments"], content))
        elif event.get("type") == "tool_use":
            part = event["part"]
            assert part["tool"].startswith("basic_memory_")
            tool_state = part["state"]
            calls.append(
                (
                    part["tool"].removeprefix("basic_memory_"),
                    tool_state["input"],
                    tool_state.get("output") or tool_state.get("error", ""),
                )
            )
    assert len(calls) == len(operations), (name, calls)
    ordered = []
    for expected_tool, expected_arguments in operations:
        matching = [
            body
            for tool, arguments, body in calls
            if tool == expected_tool and arguments == expected_arguments | {"project": "main", "output_format": "json"}
        ]
        assert len(matching) == 1, (name, expected_tool, expected_arguments, calls)
        ordered.append(json.loads(matching[0]))
    dump(f"{name}-calls", calls)
    logger.info(f"{name}: {len(calls)} verified native tool calls")
    return ordered


def content(token):
    return f"---\ntitle: Native conditional write\n---\n{token}\n"


def snapshot():
    with sqlite3.connect(state / "memory.db") as database:
        rows = database.execute(
            "SELECT file_path, markdown_content, db_checksum, db_version FROM note_content ORDER BY file_path"
        ).fetchall()
    return rows, {p.name: p.read_text() for p in corpus.glob("*.md")}


dump(
    "versions",
    {
        client: subprocess.run([client, "--version"], capture_output=True, text=True).stdout.strip()
        for client in ("codex", "opencode")
    },
)
a = run(
    "codex",
    "codex-create",
    [
        ("bm_write", {"identifier": "a.md", "content": content("original_a")}),
        ("bm_read", {"identifier": "a.md"}),
    ],
)[1]["checksum"]
b_results = run(
    "opencode",
    "opencode-create-read",
    [
        ("bm_write", {"identifier": "b.md", "content": content("original_b")}),
        ("bm_read", {"identifier": "b.md"}),
        ("bm_read", {"identifier": "a.md"}),
    ],
)
b = b_results[1]["checksum"]
assert b_results[2]["checksum"] == a
updated_a = run(
    "codex",
    "codex-update",
    [
        ("bm_read", {"identifier": "b.md"}),
        ("bm_write", {"identifier": "a.md", "content": content("winner_a"), "expected_checksum": a}),
    ],
)
assert updated_a[0]["checksum"] == b and updated_a[1]["checksum"] != a
run(
    "opencode",
    "opencode-update",
    [
        ("bm_write", {"identifier": "b.md", "content": content("winner_b"), "expected_checksum": b}),
    ],
)
winning = snapshot()
for client, identifier, checksum in (("opencode", "a.md", a), ("codex", "b.md", b)):
    conflict = run(
        client,
        f"{client}-stale",
        [
            ("bm_write", {"identifier": identifier, "content": content("stale_body"), "expected_checksum": checksum}),
        ],
    )[0]
    assert conflict["error"] == "REVISION_CONFLICT", conflict
    assert snapshot() == winning, "Stale write changed the winning database content or file"
assert "winner_a" in (corpus / "a.md").read_text() and "winner_b" in (corpus / "b.md").read_text()
assert {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "evaluation/corpus").rglob("*.md")
} == before
guards = [json.loads(path.read_text()) for path in OUT.glob("*.guard.json")]
assert len(guards) == 6 and all(not guard["blocked_connections"] for guard in guards)
assert all(set(guard["blocked_imports"]) <= {"sqlite_vec"} for guard in guards)
assert not any(p.is_file() for p in (OUT / "models").rglob("*"))
dump(
    "result",
    {
        "native_create_and_update": ["codex", "opencode"],
        "stale_write_conflict": ["codex", "opencode"],
        "winning_database_and_files_preserved": True,
        "live_corpus_unchanged": True,
        "model_free_control_only": True,
    },
)
logger.info("Both clients preserved newer native revisions after stale writes")
