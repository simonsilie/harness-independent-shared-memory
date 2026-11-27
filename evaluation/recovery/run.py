import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT.parent))
from evaluation.support import check, run_directory, sha256_file  # noqa: E402


def main(out: Path | None = None) -> None:
    out = out or run_directory(__file__)
    out.mkdir(parents=True)
    logger.info(f"Recovery artifacts: {out}")
    documents = [ROOT / "harness-independent-shared-memory.md", *sorted((ROOT / "corpus").glob("*.md"))]
    before = {str(p.relative_to(ROOT)): sha256_file(p) for p in documents}
    check(len(documents) == 21, f"Expected 21 documents, found {len(documents)}")
    (out / "manifest.json").write_text(json.dumps(before, indent=2) + "\n")
    with zipfile.ZipFile(out / "documents.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in documents:
            archive.write(path, path.relative_to(ROOT))
    restored = out / "restored"
    with zipfile.ZipFile(out / "documents.zip") as archive:
        archive.extractall(restored)
    check(
        {name: sha256_file(restored / name) for name in before} == before,
        "Restored documents differ from the originals",
    )

    state = out / "state"
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
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR": str(out / "models"),
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
        "FASTEMBED_CACHE_PATH": str(out / "models"),
        "HF_HOME": str(out / "models/huggingface"),
        "HF_HUB_OFFLINE": "1",
        "XDG_CACHE_HOME": str(out / "cache"),
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
        (out / f"{name}.stdout").write_text(result.stdout)
        (out / f"{name}.stderr").write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f"{name} failed with exit {result.returncode}; inspect saved output")
        return result.stdout

    check(not (state / "memory.db").exists(), "The isolated store already has a database")
    run("reindex", "reindex", "--full", "--search", "--project", "main")
    check((state / "memory.db").exists(), "Reindexing did not create the isolated database")
    for path in sorted((restored / "corpus").glob("*.md")):
        metadata = dict(
            (key, json.loads(value))
            for key, value in (line.split(": ", 1) for line in path.read_text().split("---\n", 2)[1].splitlines())
        )
        note = json.loads(run(path.stem, "tool", "read", path.stem, "--project", "main", "--json"))
        check(note["frontmatter"] == metadata, f"Served frontmatter differs for {path.name}")
        check(
            (path.parent / metadata["source_uri"]).resolve() == restored / "harness-independent-shared-memory.md",
            f"{path.name} does not point to the restored source document",
        )
        logger.info(f"Restored and read {path.stem}")
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
    check(
        {row["permalink"] for row in search["results"]} == {p.stem for p in (restored / "corpus").glob("*.md")},
        "Text search did not return exactly the restored notes",
    )
    check(
        {name: sha256_file(restored / name) for name in before} == before,
        "Restored documents changed during the drill",
    )
    check(
        {str(p.relative_to(ROOT)): sha256_file(p) for p in documents} == before,
        "Original documents changed during the drill",
    )
    summary = {
        "documents_restored": 21,
        "notes_read_with_matching_metadata": 20,
        "text_search_returned_notes": len(search["results"]),
        "fresh_index_rebuilt": True,
        "restored_bytes_unchanged": True,
        "original_bytes_unchanged": True,
        "scope": "Document and metadata restore into an isolated SQLite store; live database was not copied or replaced.",
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
