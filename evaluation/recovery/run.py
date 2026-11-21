import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
OUT.mkdir(parents=True)
print(f"Recovery artifacts: {OUT}", flush=True)
documents = [ROOT / "harness-independent-shared-memory.md", *sorted((ROOT / "corpus").glob("*.md"))]
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in documents}
assert len(documents) == 21
(OUT / "manifest.json").write_text(json.dumps(before, indent=2) + "\n")
with zipfile.ZipFile(OUT / "documents.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in documents:
        archive.write(path, path.relative_to(ROOT))
restored = OUT / "restored"
with zipfile.ZipFile(OUT / "documents.zip") as archive:
    archive.extractall(restored)
assert {name: hashlib.sha256((restored / name).read_bytes()).hexdigest() for name in before} == before

state = OUT / "state"
state.mkdir(mode=0o700)
config = json.loads((ROOT / ".state/config.json").read_text())
config["projects"] = {"main": {"path": str(restored / "corpus"), "mode": "local"}}
config["default_project"] = "main"
config["database_backend"] = "sqlite"
config["database_url"] = None
(state / "config.json").write_text(json.dumps(config, indent=2) + "\n")
(state / "config.json").chmod(0o600)
env = os.environ | {
    "BASIC_MEMORY_CONFIG_DIR": str(state),
    "BASIC_MEMORY_HOME": str(restored / "corpus"),
    "BASIC_MEMORY_FORCE_LOCAL": "true",
    "BASIC_MEMORY_AUTO_UPDATE": "false",
    "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "text",
    "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "fastembed",
    "BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR": str(OUT / "models"),
    "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
    "FASTEMBED_CACHE_PATH": str(OUT / "models"),
    "HF_HOME": str(OUT / "models/huggingface"),
    "HF_HUB_OFFLINE": "1",
    "XDG_CACHE_HOME": str(OUT / "cache"),
}


def run(name, *arguments):
    result = subprocess.run(
        [str(Path(sys.executable).with_name("basic-memory")), *arguments],
        cwd=restored,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    (OUT / f"{name}.stdout").write_text(result.stdout)
    (OUT / f"{name}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name} failed with exit {result.returncode}; inspect saved output")
    return result.stdout


assert not (state / "memory.db").exists()
run("reindex", "reindex", "--full", "--search", "--project", "main")
assert (state / "memory.db").exists()
for path in sorted((restored / "corpus").glob("*.md")):
    metadata = dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in path.read_text().split("---\n", 2)[1].splitlines())
    )
    note = json.loads(run(path.stem, "tool", "read", path.stem, "--project", "main", "--json"))
    assert note["frontmatter"] == metadata, path.name
    assert (path.parent / metadata["source_uri"]).resolve() == restored / "harness-independent-shared-memory.md"
    print(f"Restored and read {path.stem}", flush=True)
search = json.loads(
    run(
        "search",
        "tool",
        "search",
        "scope OR memory OR SQLite OR proposal OR accepted OR project OR handover OR text OR retries OR expiry",
        "--mode",
        "text",
        "--page-size",
        "100",
        "--project",
        "main",
        "--json",
    )
)
assert {row["permalink"] for row in search["results"]} == {p.stem for p in (restored / "corpus").glob("*.md")}
assert {name: hashlib.sha256((restored / name).read_bytes()).hexdigest() for name in before} == before
assert {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in documents} == before
summary = {
    "documents_restored": 21,
    "notes_read_with_matching_metadata": 20,
    "text_search_returned_notes": len(search["results"]),
    "fresh_index_rebuilt": True,
    "restored_bytes_unchanged": True,
    "original_bytes_unchanged": True,
    "scope": "Document and metadata restore into an isolated SQLite store; live database was not copied or replaced.",
}
(OUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
