import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
from evaluation.support import check, run_directory, sha256_file  # noqa: E402


@dataclass
class CorpusNote:
    path: Path
    metadata: dict


def frontmatter(markdown):
    return dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in markdown.split("---\n", 2)[1].splitlines())
    )


def text_of(result: CallToolResult) -> str:
    block = result.content[0]
    if not isinstance(block, TextContent):
        raise RuntimeError(f"Expected a text block, got {block!r}")
    return block.text


async def verify(out: Path, notes: dict[str, CorpusNote], source: Path, source_revision: str) -> list[float]:
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
                check(not search.is_error, f"bm_search failed for {stem}: {search.content}")
                payload = json.loads(text_of(search))
                payload = payload.get("result", payload) if isinstance(payload, dict) else json.loads(payload)
                rows = payload["results"]
                (out / f"search-{stem}.json").write_text(json.dumps(rows, indent=2) + "\n")
                permalinks = [row["permalink"] for row in rows]
                check(stem in permalinks[:5], f"{stem} is not in the top five results: {permalinks}")
                row = next(row for row in rows if row["permalink"] == stem)
                check(row["title"] == metadata["title"], f"Search title differs for {stem}: {row['title']}")
                read = await session.call_tool("bm_read", arguments={"identifier": stem, "project": "main"})
                check(not read.is_error, f"bm_read failed for {stem}: {read.content}")
                served = text_of(read)
                (out / f"read-{stem}.md").write_text(served)
                check(served == note.path.read_text(), f"Served bytes differ from corpus for {stem}")
                served_metadata = frontmatter(served)
                check(served_metadata["id"] == metadata["id"], f"Served id differs: {served_metadata}")
                check(
                    served_metadata["source_revision"] == source_revision,
                    f"Served source revision differs: {served_metadata}",
                )
                source_path = (note.path.parent / served_metadata["source_uri"]).resolve()
                check(source_path == source.resolve(), f"{stem} points to {source_path}")
                check(
                    sha256_file(source_path) == source_revision.removeprefix("sha256:"),
                    f"Source document for {stem} does not match its revision",
                )
                latencies.append((time.monotonic() - started) * 1000)
                logger.info(f"Verified {stem}")
    return latencies


def main(out: Path | None = None) -> None:
    out = out or run_directory(__file__)
    out.mkdir(parents=True)
    logger.info(f"Evidence artifacts: {out}")

    source = ROOT / "evaluation/harness-independent-shared-memory.md"
    source_revision = "sha256:" + sha256_file(source)
    notes: dict[str, CorpusNote] = {}
    for path in sorted((ROOT / "evaluation/corpus").glob("*.md")):
        metadata = frontmatter(path.read_text())
        check(
            metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision,
            f"{path} is not an accepted note of the current source revision",
        )
        notes[path.stem] = CorpusNote(path=path, metadata=metadata)
    check(len(notes) == 20, f"Expected 20 corpus notes, found {len(notes)}")
    check(
        all(note.metadata["id"] == note.metadata["permalink"] == stem for stem, note in notes.items()),
        "Every corpus note id and permalink must match its file name",
    )

    hashes = {note.path.name: sha256_file(note.path) for note in notes.values()}
    (out / "corpus-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    version = subprocess.run(["./bm", "--version"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    check(version.returncode == 0, f"Basic Memory version check failed: {version.stderr}")
    (out / "basic-memory-version.txt").write_text(version.stdout)

    latencies = asyncio.run(verify(out, notes, source, source_revision))
    check(
        {note.path.name: sha256_file(note.path) for note in notes.values()} == hashes,
        "Corpus changed during verification",
    )
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
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
