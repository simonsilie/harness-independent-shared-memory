import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import basic_memory
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
OUT.mkdir(parents=True)
print(f"Native MCP/watcher probe artifacts: {OUT}", flush=True)
assert version("basic-memory") == os.environ.get("PHASE1B_EXPECTED_VERSION", "1.0.0")
installed = "--installed-semantic-disabled" in sys.argv
semantic_disabled = installed or "--semantic-disabled" in sys.argv
before = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "evaluation/corpus").rglob("*.md")
}
state = OUT / "state"
corpus = OUT / "corpus"
state.mkdir(mode=0o700)
corpus.mkdir()
(state / "config.json").write_text(
    json.dumps(
        {
            "projects": {"main": {"path": str(corpus), "mode": "local"}},
            "default_project": "main",
            "database_backend": "sqlite",
            "database_url": None,
            **(
                {"semantic_search_enabled": False, "default_search_type": "hybrid", "reranker_enabled": True}
                if semantic_disabled
                else {}
            ),
        }
    )
    + "\n"
)
# Do not inherit another deployment's routing, credentials or test-mode overrides.
# Unlike the CLI probe, BASIC_MEMORY_DEFAULT_SEARCH_TYPE stays unset: the default
# search mode must fall back to text on its own when semantic search is unavailable.
env = {k: v for k, v in os.environ.items() if not k.startswith(("BASIC_MEMORY_", "PHASE1B_", "OPENAI_", "LOGFIRE_"))}
env.pop("PYTEST_CURRENT_TEST", None)
if installed:
    env.pop("PYTHONPATH", None)
env.update(
    {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(corpus),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        # FastMCP's startup banner checks PyPI when its version cache is empty,
        # which would register as a blocked outbound connection on a fresh runner.
        "FASTMCP_CHECK_FOR_UPDATES": "off",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "fastembed",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR": str(OUT / "models"),
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
        "FASTEMBED_CACHE_PATH": str(OUT / "models"),
        "HF_HOME": str(OUT / "models/huggingface"),
        "HF_HUB_OFFLINE": "1",
        "XDG_CACHE_HOME": str(OUT / "cache"),
        "TMPDIR": str(OUT),
    }
)
SERVER = Path(__file__).with_name("mcp_server_guard.py")
vector_runtime_version = None
if semantic_disabled:
    import sqlite_vec

    with sqlite3.connect(":memory:") as connection:
        connection.enable_load_extension(True)
        connection.load_extension(sqlite_vec.loadable_path())
        vector_runtime_version = connection.execute("SELECT vec_version()").fetchone()[0]

    if not installed:
        package_root = OUT / "package"
        shutil.copytree(
            Path(basic_memory.__file__).parent,
            package_root / "basic_memory",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        patch_args = [
            "patch",
            "--batch",
            "--force",
            "--fuzz=0",
            "-p1",
            "-i",
            str(ROOT / "patches/basic-memory-semantic-disable.patch"),
        ]
        existing = subprocess.run(
            [*patch_args, "--reverse", "--dry-run"],
            cwd=package_root,
            capture_output=True,
            text=True,
        )
        if existing.returncode == 0:
            (OUT / "patch.stdout").write_text("Installed source already contains the patch.\n" + existing.stdout)
        else:
            applied = subprocess.run(patch_args, cwd=package_root, capture_output=True, text=True, check=True)
            (OUT / "patch.stdout").write_text(applied.stdout)
        env["PYTHONPATH"] = str(package_root)
saved = 0


def dump(name, payload):
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


async def call(session, name, tool, arguments, expect_error=False):
    global saved
    result = await asyncio.wait_for(session.call_tool(tool, arguments), 180)
    text = "".join(block.text for block in result.content if hasattr(block, "text"))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = text
    if name:
        dump(name, payload)
    if expect_error:
        assert result.is_error, f"{tool} unexpectedly succeeded: {text}"
        return text
    assert not result.is_error, f"{tool} returned an error: {text}"
    return payload


def server_params(name):
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER), "mcp", "--transport", "stdio", "--project", "main"],
        env=env
        | {
            "PHASE1B_GUARD_PATH": str(OUT / f"{name}.guard.json"),
            "PHASE1B_ALLOW_SQLITE_VEC": "1" if semantic_disabled or "--installed-semantic-stack" in sys.argv else "0",
        },
    )


async def with_session(name, work):
    with (OUT / f"{name}.stderr").open("w") as errlog:
        async with stdio_client(server_params(name), errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), 180)
                return await work(session)


async def phase1(session):
    tools = await asyncio.wait_for(session.list_tools(), 60)
    dump("tools", sorted(tool.name for tool in tools.tools))
    assert {"bm_read", "bm_search", "bm_write"} <= {tool.name for tool in tools.tools}
    created = await call(
        session,
        "mcp-write",
        "bm_write",
        {
            "identifier": "watcher.md",
            "project": "main",
            "content": "---\ntitle: MCP watcher probe\n---\nmcpwatchertoken\n",
        },
    )
    # No per-note `embed` opt-out on purpose: the global path must work without it.
    assert "watcher.md" in str(created)
    search = await call(
        session,
        "mcp-default-search",
        "bm_search",
        {"query": "mcpwatchertoken", "project": "main", "output_format": "json"},
    )
    assert [row["permalink"] for row in search["results"]] == ["main/watcher"], search
    # The default mode fell back to text; an explicit semantic mode must refuse cleanly.
    vector = await call(
        session,
        "vector-mode-refused",
        "bm_search",
        {"query": "mcpwatchertoken", "project": "main", "mode": "vector", "output_format": "json"},
        expect_error=True,
    )
    lowered = vector.lower()
    assert "semantic" in lowered or "sqlite-vec" in lowered, vector
    if semantic_disabled:
        await call(
            session,
            "hybrid-mode-refused",
            "bm_search",
            {"query": "mcpwatchertoken", "project": "main", "mode": "hybrid", "output_format": "json"},
            expect_error=True,
        )
        scoped = await call(
            session,
            "scoped-default-search",
            "bm_search",
            {"query": "mcpwatchertoken", "projects": ["main"], "output_format": "json"},
        )
        assert [row["permalink"] for row in scoped["results"]] == ["main/watcher"], scoped
    # Watcher evidence: an external file edit that no client wrote.
    (corpus / "observed.md").write_text("---\ntitle: Observed file\n---\nwatcherfiletoken\n")
    deadline = time.monotonic() + 120
    while True:
        search = await call(
            session, None, "bm_search", {"query": "watcherfiletoken", "project": "main", "output_format": "json"}
        )
        if [row["permalink"] for row in search["results"]] == ["main/observed"]:
            break
        assert time.monotonic() < deadline, "the watcher did not index the external file edit"
        await asyncio.sleep(2)
    dump("watcher-search", search)
    # Dwell: keep the server and watcher running while nothing happens.
    await asyncio.sleep(30)
    still = await call(
        session,
        "watcher-still-search",
        "bm_search",
        {"query": "mcpwatchertoken OR watcherfiletoken", "project": "main", "output_format": "json"},
    )
    assert {row["permalink"] for row in still["results"]} == {"main/watcher", "main/observed"}, still


async def phase2(session):
    read = await call(
        session, "read-after-restart", "bm_read", {"identifier": "watcher", "project": "main", "output_format": "json"}
    )
    assert "mcpwatchertoken" in read["content"], read
    search = await call(
        session,
        "search-after-restart",
        "bm_search",
        {"query": "mcpwatchertoken OR watcherfiletoken", "project": "main", "output_format": "json"},
    )
    assert {row["permalink"] for row in search["results"]} == {"main/watcher", "main/observed"}, search


asyncio.run(with_session("server-1", phase1))
asyncio.run(with_session("server-2", phase2))

# Disabled semantics must ignore an unusable provider; enabled mode still rejects it.
crash = subprocess.run(
    [
        sys.executable,
        *([str(SERVER)] if semantic_disabled else ["-c", "from basic_memory.cli.main import app; app()"]),
        "tool",
        "search",
        "mcpwatchertoken",
        "--project",
        "main",
    ],
    cwd=OUT,
    env=env
    | {
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "none",
        **(
            {"PHASE1B_GUARD_PATH": str(OUT / "cli.guard.json"), "PHASE1B_ALLOW_SQLITE_VEC": "1"}
            if semantic_disabled
            else {}
        ),
    },
    capture_output=True,
    text=True,
    timeout=180,
)
(OUT / "provider-off.stdout").write_text(crash.stdout)
(OUT / "provider-off.stderr").write_text(crash.stderr)
if semantic_disabled:
    assert crash.returncode == 0, crash.stderr
else:
    assert crash.returncode != 0 and "Unsupported semantic embedding provider" in crash.stderr

guards = {name: json.loads((OUT / f"{name}.guard.json").read_text()) for name in ("server-1", "server-2")}
if semantic_disabled:
    guards["cli"] = json.loads((OUT / "cli.guard.json").read_text())
log_text = (state / "basic-memory.log").read_text()
if not semantic_disabled:
    assert "Semantic search disabled" in log_text and "Falling back to keyword-only search" in log_text, (
        "the keyword-only fallback was not logged"
    )
assert "failed_files=0" in log_text, "the watcher reported failed files"
if semantic_disabled:
    assert all(not guard["blocked_imports"] and not guard["blocked_connections"] for guard in guards.values()), guards
    with sqlite3.connect(state / "memory.db") as connection:
        assert not connection.execute("SELECT name FROM sqlite_master WHERE name='search_vector_embeddings'").fetchall()
else:
    assert "sqlite_vec" in guards["server-1"]["blocked_imports"], "the sqlite-vec control was not exercised"
assert not any(p.is_file() for p in (OUT / "models").rglob("*")), "the server downloaded embedding models"
assert {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "evaluation/corpus").rglob("*.md")
} == before
if installed:
    assert all(
        Path(guard["basic_memory_source"]).resolve() == Path(basic_memory.__file__).resolve()
        for guard in guards.values()
    ), guards
summary = {
    "installed_package_used": installed,
    "basic_memory_version": version("basic-memory"),
    "inference_unavailable": (
        "fastembed, onnxruntime, torch, transformers and litellm imports plus outbound Python sockets blocked; sqlite_vec available"
        if semantic_disabled
        else "sqlite_vec, fastembed, onnxruntime, torch, transformers and litellm imports plus outbound Python sockets blocked in both MCP server processes"
    ),
    **({"installed_sqlite_vec_version": vector_runtime_version} if semantic_disabled else {}),
    "mcp_server_boot_and_tools": True,
    "semantic_disabled_fallback_logged": not semantic_disabled,
    "semantic_disabled_by_configuration": semantic_disabled,
    "explicit_vector_mode_refused": True,
    "default_search_mode_without_env_override": "text",
    "mcp_write_and_default_search": True,
    "optional_semantic_probe_failed_cleanly": "Client error: QUERY" in log_text,
    "watcher_indexed_external_file_edit": True,
    "long_running_dwell_seconds": 30,
    "restart_read_and_search": True,
    "per_note_embed_opt_out_used": False,
    "embedding_models_downloaded": False,
    "fastembed_import_attempts_in_servers": sum(
        guard["blocked_imports"].count("fastembed") for guard in guards.values()
    ),
    "provider_off_configuration_exit": crash.returncode,
    "provider_off_configuration_error": None if semantic_disabled else "Unsupported semantic embedding provider",
    "live_corpus_unchanged": True,
    "limits": ("Installed package" if installed else "Isolated patched package")
    + " with semantic_search_enabled=false; disposable data, productive storage unchanged. SQLite MCP/watcher/restart verified, no live PostgreSQL or remote service verification."
    if semantic_disabled
    else (
        "One MCP stdio client per server process with a 30 s dwell, not real model traffic. "
        "The keyword-only fallback was simulated by blocking the sqlite_vec import; a deployment "
        "keeps it by not providing sqlite-vec. No protected execution boundary, no proposal/handover "
        "workflow, no portable recovery. No Phase 1B rollout gate is passed by this run."
    ),
}
(OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
