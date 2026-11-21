import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-native-coverage")
OUT.mkdir(parents=True)
print(f"Native memory coverage artifacts: {OUT}", flush=True)
assert version("basic-memory") == "1.0.0"
state = OUT / "state"
state.mkdir()
projects = {name: OUT / name for name in ("personal", "alpha", "beta")}
for directory in projects.values():
    directory.mkdir()
(state / "config.json").write_text(
    json.dumps(
        {
            "projects": {name: {"path": str(path), "mode": "local"} for name, path in projects.items()},
            "default_project": "alpha",
            "database_backend": "sqlite",
            "database_url": None,
        }
    )
    + "\n"
)
env = {k: v for k, v in os.environ.items() if not k.startswith(("BASIC_MEMORY_", "PHASE1B_", "OPENAI_", "LOGFIRE_"))}
env.pop("PYTEST_CURRENT_TEST", None)
env.update(
    {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(projects["alpha"]),
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
GUARD = Path(__file__).with_name("mcp_server_guard.py")


def snapshot(directory):
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*")
        if p.is_file()
    }


def dump(name, payload):
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")


before = snapshot(ROOT / "evaluation/corpus")


async def call(session, name, tool, **arguments):
    result = await asyncio.wait_for(session.call_tool(tool, arguments | {"output_format": "json"}), 180)
    raw = "".join(block.text for block in result.content if hasattr(block, "text"))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = raw
    dump(name, payload)
    assert not result.is_error, payload
    return payload


async def search(session, name, expected, **arguments):
    result = await call(
        session, name, "bm_search", query="coveragetoken", mode="text", items=["note"], page_size=100, **arguments
    )
    assert {row["permalink"] for row in result["results"]} == set(expected), result


async def check(session):
    inventory = await session.list_tools()
    dump("tools", [tool.model_dump() for tool in inventory.tools])
    fixtures = [
        ("personal", "defaults", "durable", "active", "2026-11-17T00:00:00Z"),
        ("alpha", "knowledge", "durable", "active", "2026-11-17T00:00:00Z"),
        ("alpha", "handover", "temporary", "active", "2026-11-17T00:00:00Z"),
        ("alpha", "inactive", "temporary", "active", "2026-10-01T00:00:00Z"),
        ("alpha", "completed", "temporary", "completed", "2026-11-17T00:00:00Z"),
        ("alpha", "archive/old", "temporary", "archived", "2026-10-01T00:00:00Z"),
        ("beta", "handover", "temporary", "active", "2026-11-17T00:00:00Z"),
    ]
    for project, path, kind, status, updated in fixtures:
        content = (
            f"---\ntitle: {project} {path}\nkind: {kind}\nstatus: {status}\n"
            f"last_activity: '{updated}'\nsource: disposable coverage fixture\n---\n"
            f"coveragetoken {project} {path}\n"
        )
        await call(
            session,
            f"write-{project}-{path.replace('/', '-')}",
            "bm_write",
            project=project,
            identifier=f"{path}.md",
            content=content,
        )
    alpha = [f"alpha/{path}" for project, path, *_ in fixtures if project == "alpha"]
    await search(session, "single-project", alpha, project="alpha")
    await search(session, "personal-plus-project", ["personal/defaults", *alpha], projects=["personal", "alpha"])
    await search(session, "explicit-cross-project", ["beta/handover"], project="beta")
    await search(session, "all-projects", ["personal/defaults", "beta/handover", *alpha], all_projects=True)
    await search(
        session,
        "active-filter-still-includes-inactive",
        ["alpha/knowledge", "alpha/handover", "alpha/inactive"],
        project="alpha",
        filters={"status": "active"},
    )
    await search(session, "archive-explicit", ["alpha/archive/old"], project="alpha", filters={"status": "archived"})
    await search(
        session,
        "temporary-with-cutoff",
        ["alpha/handover"],
        project="alpha",
        filters={"status": "active", "kind": "temporary", "last_activity": {"$gte": "2026-11-10T00:00:00Z"}},
    )
    original = await call(session, "read-before-restore", "bm_read", project="alpha", identifier="archive/old.md")
    restored = (
        original["content"]
        .replace("status: archived", "status: active")
        .replace("2026-10-01T00:00:00Z", "2026-11-17T00:00:00Z")
    )
    await call(
        session,
        "restore-conditional",
        "bm_write",
        project="alpha",
        identifier="archive/old.md",
        content=restored,
        expected_checksum=original["checksum"],
    )
    await search(
        session,
        "restore-visible",
        ["alpha/handover", "alpha/archive/old"],
        project="alpha",
        filters={"status": "active", "kind": "temporary", "last_activity": {"$gte": "2026-11-10T00:00:00Z"}},
    )
    await call(
        session,
        "rearchive-conditional",
        "bm_write",
        project="alpha",
        identifier="archive/old.md",
        content=original["content"],
        expected_checksum=(
            await call(session, "read-restored", "bm_read", project="alpha", identifier="archive/old.md")
        )["checksum"],
    )


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(GUARD), "mcp", "--transport", "stdio"],
        env=env | {"PHASE1B_GUARD_PATH": str(OUT / "server.guard.json")},
    )
    with (OUT / "server.stderr").open("w") as errlog:
        async with stdio_client(params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), 180)
                await check(session)


asyncio.run(main())
source_before_export = {name: snapshot(path) for name, path in projects.items()}
for name in projects:
    result = subprocess.run(
        [sys.executable, str(GUARD), "okf", "export", str(OUT / "export" / name), "--project", name, "--json"],
        env=env | {"PHASE1B_GUARD_PATH": str(OUT / f"export-{name}.guard.json")},
        capture_output=True,
        text=True,
        timeout=180,
    )
    (OUT / f"export-{name}.stdout").write_text(result.stdout)
    (OUT / f"export-{name}.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stderr + result.stdout
    assert f"# {name}\n" in (OUT / "export" / name / "index.md").read_text()
    for source in projects[name].rglob("*.md"):
        exported = OUT / "export" / name / source.relative_to(projects[name])
        assert exported.exists(), exported
        content = exported.read_text()
        assert f"permalink: {name}/" in content, exported
        for line in source.read_text().splitlines():
            if line.startswith(("coveragetoken", "kind:", "status:", "last_activity:", "source:")):
                assert line in content, (exported, line)
assert source_before_export == {name: snapshot(path) for name, path in projects.items()}
assert snapshot(ROOT / "evaluation/corpus") == before
for path in OUT.glob("*.guard.json"):
    guard = json.loads(path.read_text())
    assert guard["blocked_connections"] == 0, guard
    assert not any(name != "sqlite_vec" for name in guard["blocked_imports"]), guard
assert not any(p.is_file() for p in (OUT / "models").rglob("*"))
dump(
    "result",
    {
        "basic_memory_version": version("basic-memory"),
        "personal_plus_project_and_explicit_cross_project": "passed with explicit scope",
        "lifecycle": "metadata filters and conditional restore passed; unfiltered recall includes archived, completed and authored inactive entries",
        "export": "all three per-project OKF bundles preserve fixture bodies and lifecycle/source metadata; source bytes unchanged",
        "live_corpus_unchanged": True,
        "limits": "Disposable native MCP/API check with sqlite_vec fallback guard; no productive configuration or automatic lifecycle, no elapsed seven-day test or client instruction verification.",
    },
)
print((OUT / "result.json").read_text())
