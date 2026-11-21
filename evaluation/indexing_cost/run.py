import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
MEASURED_RUNS = [
    # The embedding pass requires indexed entities, so it reuses the same store
    # after the search index run; its store_bytes therefore repeat that run.
    ("state-search", "search-index", ["reindex", "--full", "--search", "--project", "main"]),
    ("state-search", "embeddings-only", ["reindex", "--full", "--embeddings", "--project", "main"]),
    ("state-full", "full-reindex", ["reindex", "--full", "--project", "main"]),
]


def main(out=None):
    if out is None:
        out = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    logger.info(f"Indexing-cost artifacts: {out}")

    source_revision = (
        "sha256:" + hashlib.sha256((ROOT / "harness-independent-shared-memory.md").read_bytes()).hexdigest()
    )
    notes = sorted((ROOT / "corpus").glob("*.md"))
    assert len(notes) == 20
    corpus = out / "corpus"
    corpus.mkdir()
    hashes = {}
    for path in notes:
        text = path.read_text()
        metadata = dict(
            (key, json.loads(value))
            for key, value in (line.split(": ", 1) for line in text.split("---\n", 2)[1].splitlines())
        )
        assert metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision, path
        shutil.copyfile(path, corpus / path.name)
        hashes[path.name] = hashlib.sha256((corpus / path.name).read_bytes()).hexdigest()
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in corpus.glob("*.md")} == hashes
    (out / "corpus-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")

    version = subprocess.run(
        [str(Path(sys.executable).with_name("basic-memory")), "--version"], capture_output=True, text=True, timeout=120
    )
    assert version.returncode == 0, version.stderr
    (out / "basic-memory-version.txt").write_text(version.stdout)

    results = {}
    configs = {}
    for state_name, name, arguments in MEASURED_RUNS:
        state = out / state_name
        if state_name not in configs:
            state.mkdir(mode=0o700)
            config = json.loads((ROOT / ".state/config.json").read_text())
            config["projects"] = {"main": {"path": str(corpus), "mode": "local"}}
            config["default_project"] = "main"
            config["database_backend"] = "sqlite"
            config["database_url"] = None
            config_path = state / "config.json"
            config_path.write_text(json.dumps(config, indent=2) + "\n")
            config_path.chmod(0o600)
            configs[state_name] = True
        env = os.environ | {
            "BASIC_MEMORY_CONFIG_DIR": str(state),
            "BASIC_MEMORY_HOME": str(corpus),
            "BASIC_MEMORY_FORCE_LOCAL": "true",
            "BASIC_MEMORY_AUTO_UPDATE": "false",
            "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "text",
            "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "fastembed",
            "BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR": str(ROOT.parent / ".models"),
            "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
            "FASTEMBED_CACHE_PATH": str(ROOT.parent / ".models"),
            "HF_HOME": str(ROOT.parent / ".models/huggingface"),
            "HF_HUB_OFFLINE": "1",
            "XDG_CACHE_HOME": str(out / "cache"),
        }
        assert not (state / "memory.db").exists() or name == "embeddings-only", f"{name} found an unexpected store"
        started = time.monotonic()
        with (out / f"{name}.stdout").open("w") as stdout, (out / f"{name}.stderr").open("w") as stderr:
            process = subprocess.Popen(
                [str(Path(sys.executable).with_name("basic-memory")), *arguments],
                cwd=corpus,
                env=env,
                stdout=stdout,
                stderr=stderr,
            )
            _, status, usage = os.wait4(process.pid, 0)
        wall_s = time.monotonic() - started
        process.returncode = os.waitstatus_to_exitcode(status)
        assert process.returncode == 0, f"{name} failed with exit {process.returncode}; inspect saved output"
        assert (state / "memory.db").exists(), f"{name} produced no store"
        results[name] = {
            "command": arguments,
            "wall_s": round(wall_s, 2),
            # ru_maxrss is reported in bytes on macOS (kilobytes on Linux).
            "peak_rss_bytes": usage.ru_maxrss,
            "peak_rss_mb": round(usage.ru_maxrss / (1024 * 1024), 1),
            "store_bytes": (state / "memory.db").stat().st_size,
        }
        logger.info(f"{name}: {results[name]['wall_s']} s, {results[name]['peak_rss_mb']} MB peak RSS")

    # Sanity checks, run separately so they do not pollute the measurements.
    search = subprocess.run(
        [
            str(Path(sys.executable).with_name("basic-memory")),
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
        ],
        cwd=corpus,
        env=env | {"BASIC_MEMORY_CONFIG_DIR": str(out / "state-search")},
        capture_output=True,
        text=True,
        timeout=180,
    )
    (out / "verify-search.stdout").write_text(search.stdout)
    (out / "verify-search.stderr").write_text(search.stderr)
    assert search.returncode == 0, search.stderr
    returned = len(json.loads(search.stdout)["results"])
    assert returned == 20, f"Text search returned {returned} notes after indexing"
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in corpus.glob("*.md")} == hashes
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in notes} == hashes

    summary = {
        "notes": len(notes),
        "runs": results,
        "model_cache": "project-local .models (pre-cached BAAI/bge-small-en-v1.5, HF_HUB_OFFLINE=1, no download)",
        "basic_memory_version": version.stdout.strip(),
        "text_search_notes_after_indexing": returned,
        "corpus_unchanged": True,
        "scope": (
            "Isolated SQLite stores, one per run; the live store was not touched. "
            "Wall time and peak RSS measure the reindex process itself."
        ),
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
