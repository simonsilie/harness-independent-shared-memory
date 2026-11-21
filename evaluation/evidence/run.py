import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
OUT.mkdir(parents=True)
print(f"Evidence artifacts: {OUT}", flush=True)

source = ROOT / "evaluation/harness-independent-shared-memory.md"
source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()


@dataclass
class CorpusNote:
    path: Path
    metadata: dict


def frontmatter(markdown):
    return dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in markdown.split("---\n", 2)[1].splitlines())
    )


notes: dict[str, CorpusNote] = {}
for path in sorted((ROOT / "evaluation/corpus").glob("*.md")):
    metadata = frontmatter(path.read_text())
    assert metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision, path
    notes[path.stem] = CorpusNote(path=path, metadata=metadata)
assert len(notes) == 20
assert all(note.metadata["id"] == note.metadata["permalink"] == stem for stem, note in notes.items())

hashes = {note.path.name: hashlib.sha256(note.path.read_bytes()).hexdigest() for note in notes.values()}
(OUT / "corpus-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
version = subprocess.run(["./bm", "--version"], capture_output=True, text=True, cwd=ROOT, timeout=120)
assert version.returncode == 0, version.stderr
(OUT / "basic-memory-version.txt").write_text(version.stdout)


def text_of(result: CallToolResult) -> str:
    block = result.content[0]
    assert isinstance(block, TextContent), block
    return block.text


async def verify() -> list[float]:
    parameters = StdioServerParameters(
        command=str(ROOT / "evaluation/bm"),
        args=["mcp", "--project", "main"],
        cwd=str(ROOT),
        env=os.environ | {"HF_HUB_OFFLINE": "1"},
    )
    latencies: list[float] = []
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            for stem, note in sorted(notes.items()):
                metadata = note.metadata
                started = time.monotonic()
                search = await session.call_tool(
                    "bm_search",
                    arguments={
                        "query": metadata["title"],
                        "mode": "text",
                        "page_size": 5,
                        "output_format": "json",
                        "project": "main",
                    },
                )
                assert not search.is_error, (stem, search.content)
                payload = json.loads(text_of(search))
                payload = payload.get("result", payload) if isinstance(payload, dict) else json.loads(payload)
                rows = payload["results"]
                (OUT / f"search-{stem}.json").write_text(json.dumps(rows, indent=2) + "\n")
                permalinks = [row["permalink"] for row in rows]
                assert stem in permalinks[:5], (stem, permalinks)
                row = next(row for row in rows if row["permalink"] == stem)
                assert row["title"] == metadata["title"], (stem, row["title"])
                read = await session.call_tool("bm_read", arguments={"identifier": stem, "project": "main"})
                assert not read.is_error, (stem, read.content)
                served = text_of(read)
                (OUT / f"read-{stem}.md").write_text(served)
                assert served == note.path.read_text(), f"Served bytes differ from corpus for {stem}"
                served_metadata = frontmatter(served)
                assert served_metadata["id"] == metadata["id"], served_metadata
                assert served_metadata["source_revision"] == source_revision, served_metadata
                source_path = (note.path.parent / served_metadata["source_uri"]).resolve()
                assert source_path == source.resolve(), (stem, source_path)
                assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_revision.removeprefix("sha256:")
                latencies.append((time.monotonic() - started) * 1000)
                print(f"Verified {stem}", flush=True)
    return latencies


latencies = asyncio.run(verify())
assert {note.path.name: hashlib.sha256(note.path.read_bytes()).hexdigest() for note in notes.values()} == hashes
summary = {
    "notes_verified": len(notes),
    "search_results_with_stable_identity": len(notes),
    "reads_served_exact_corpus_bytes": True,
    "reads_served_source_revision": len(notes),
    "source_documents_available": True,
    "source_revision": source_revision,
    "basic_memory_version": version.stdout.strip(),
    "server_command": ["./bm", "mcp", "--project", "main"],
    "tools_called": ["bm_search", "bm_read"],
    "latency_ms": {
        "min": round(min(latencies)),
        "median": round(statistics.median(latencies)),
        "max": round(max(latencies)),
    },
    "scope": (
        "Read-only verification of the live engine serving the evaluation clients "
        "(same server command); no mutation tools and no corpus writes."
    ),
}
(OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
