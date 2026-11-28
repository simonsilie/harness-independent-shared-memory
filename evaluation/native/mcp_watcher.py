import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import basic_memory
from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.support import client_environment, sha256_file  # noqa: E402

OUT = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
OUT.mkdir(parents=True)
logger.info(f"Native MCP/watcher probe artifacts: {OUT}")
installed_version = version("basic-memory")
expected_version = os.environ.get("PHASE1B_EXPECTED_VERSION")
if expected_version is None:
    assert installed_version.partition("+")[0] == "1.0.0"
else:
    assert installed_version == expected_version
installed = "--installed" in sys.argv
before = {str(p.relative_to(ROOT)): sha256_file(p) for p in (ROOT / "evaluation/corpus").rglob("*.md")}
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
        }
    )
    + "\n"
)
# Do not inherit another deployment's routing, credentials or test-mode overrides.
# Unlike the CLI probe, BASIC_MEMORY_DEFAULT_SEARCH_TYPE stays unset: the default
# search mode must fall back to text on its own when semantic search is unavailable.
env = client_environment("BASIC_MEMORY_", "PHASE1B_", "OPENAI_", "LOGFIRE_")
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


def dump(name, payload):
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


async def call(session, name, tool, arguments, expect_error=False):
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
        env=env | {"PHASE1B_GUARD_PATH": str(OUT / f"{name}.guard.json")},
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

crash = subprocess.run(
    [
        sys.executable,
        "-c",
        "from basic_memory.cli.main import app; app()",
        "tool",
        "search",
        "mcpwatchertoken",
        "--project",
        "main",
    ],
    cwd=OUT,
    env=env | {"BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "none"},
    capture_output=True,
    text=True,
    timeout=180,
)
(OUT / "provider-off.stdout").write_text(crash.stdout)
(OUT / "provider-off.stderr").write_text(crash.stderr)
assert crash.returncode != 0 and "Unsupported semantic embedding provider" in crash.stderr

guards = {name: json.loads((OUT / f"{name}.guard.json").read_text()) for name in ("server-1", "server-2")}
log_text = (state / "basic-memory.log").read_text()
assert "Semantic search disabled" in log_text and "Falling back to keyword-only search" in log_text, (
    "the keyword-only fallback was not logged"
)
assert "failed_files=0" in log_text, "the watcher reported failed files"
assert "sqlite_vec" in guards["server-1"]["blocked_imports"], "the sqlite-vec control was not exercised"
assert not any(p.is_file() for p in (OUT / "models").rglob("*")), "the server downloaded embedding models"
assert {str(p.relative_to(ROOT)): sha256_file(p) for p in (ROOT / "evaluation/corpus").rglob("*.md")} == before
if installed:
    assert all(
        Path(guard["basic_memory_source"]).resolve() == Path(basic_memory.__file__).resolve()
        for guard in guards.values()
    ), guards
summary = {
    "installed_package_used": installed,
    "basic_memory_version": version("basic-memory"),
    "inference_unavailable": "sqlite_vec, fastembed, onnxruntime, torch, transformers and litellm imports plus outbound Python sockets blocked in both MCP server processes",
    "mcp_server_boot_and_tools": True,
    "semantic_disabled_fallback_logged": True,
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
    "provider_off_configuration_error": "Unsupported semantic embedding provider",
    "live_corpus_unchanged": True,
    "limits": (
        "One MCP stdio client per server process with a 30 s dwell, not real model traffic. "
        "The keyword-only fallback was simulated by blocking the sqlite_vec import; a deployment "
        "keeps it by not providing sqlite-vec. No protected execution boundary, no proposal/handover "
        "workflow, no portable recovery. No Phase 1B rollout gate is passed by this run."
    ),
}
(OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
sys.stdout.write(json.dumps(summary, indent=2) + "\n")
