"""Same-version backup and isolated restore of a local Basic Memory store."""

import fcntl
import hashlib
import json
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_database(path: Path) -> closing[sqlite3.Connection]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def contained(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f"Path outside store or symbolic link: {path}")
    return resolved


def inventory(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file()}


def validate_notes(root: Path, *, destination: Path | None = None) -> None:
    config = json.loads((root / "state/config.json").read_text())
    with read_database(root / "state/memory.db") as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign key check failed")
        projects = connection.execute("SELECT id, name, path FROM project").fetchall()
        if {p["name"] for p in projects} != set(config["projects"]):
            raise ValueError("Configured/database projects differ")
        for project in projects:
            stored_path = Path(config["projects"][project["name"]]["path"])
            if Path(project["path"]) != stored_path:
                raise ValueError("Configured/database project paths differ")
            relative = stored_path.relative_to(destination) if destination is not None else stored_path
            project_root = contained(root, root / relative)
            notes = connection.execute("SELECT * FROM note_content WHERE project_id=?", (project["id"],)).fetchall()
            for note in notes:
                path = contained(project_root, project_root / note["file_path"])
                if digest(path) != note["db_checksum"] or path.read_bytes() != note["markdown_content"].encode():
                    raise ValueError(f"File/database mismatch: {path}")
            if {str(p.relative_to(project_root)) for p in project_root.rglob("*.md")} != {
                n["file_path"] for n in notes
            }:
                raise ValueError(f"Unindexed or missing Markdown in {project['name']}")


def backup(source: Path, destination: Path) -> None:
    source, destination = source.resolve(), destination.resolve()
    if destination.is_relative_to(source):
        raise ValueError("Backup must be outside the live store")
    config_path = source / "state/config.json"
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    if config["database_backend"] != "sqlite" or config.get("database_url") or config["semantic_search_enabled"]:
        raise ValueError("Expected the productive model-free SQLite configuration")
    if destination.exists():
        raise FileExistsError(f"Backup destination exists: {destination}")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent))
    try:
        (staging / "state").mkdir(mode=0o700)
        with (
            read_database(source / "state/memory.db") as live,
            closing(sqlite3.connect(staging / "state/memory.db")) as copy,
        ):
            live.backup(copy)
            # A standalone snapshot must not depend on mutable WAL/SHM sidecars.
            mode = copy.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if mode != "delete":
                raise ValueError(f"Unexpected snapshot journal mode: {mode}")
        for name, project in config["projects"].items():
            if project.get("mode") != "local":
                raise ValueError(f"Non-local project: {name}")
            path = contained(source, Path(project["path"]))
            relative = path.relative_to(source)
            for child in path.rglob("*"):
                contained(path, child)
            shutil.copytree(path, staging / relative)
            project["path"] = str(relative)
        with (source / "observations/observations.jsonl").open("rb") as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            observations = stream.read()
        for line in observations.splitlines():
            json.loads(line)
        (staging / "observations").mkdir(mode=0o700)
        (staging / "observations/observations.jsonl").write_bytes(observations)
        shutil.copyfile(source / "state/.bmignore", staging / "state/.bmignore")
        (staging / "state/config.original.json").write_bytes(config_bytes)
        (staging / "state/config.json").write_text(json.dumps(config, indent=2) + "\n")
        with closing(sqlite3.connect(staging / "state/memory.db")) as connection, connection:
            for name, project in config["projects"].items():
                connection.execute("UPDATE project SET path=? WHERE name=?", (project["path"], name))
        if config_path.read_bytes() != config_bytes:
            raise ValueError("Configuration changed during backup; retry into a new destination")
        validate_notes(staging)
        sidecars = sorted(path.name for path in (staging / "state").glob("memory.db-*"))
        if sidecars:
            raise ValueError(f"Unexpected snapshot sidecars: {', '.join(sidecars)}")
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "files": inventory(staging)}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for path in staging.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def restore(archive: Path, destination: Path) -> None:
    archive, destination = archive.resolve(), destination.resolve()
    manifest = json.loads((archive / "manifest.json").read_text())
    actual = inventory(archive)
    del actual["manifest.json"]
    if actual != manifest["files"]:
        raise ValueError("Backup manifest mismatch")
    validate_notes(archive)
    if destination.is_relative_to(archive) or archive.is_relative_to(destination):
        raise ValueError("Restore must be separate from the backup")
    if destination.exists():
        raise FileExistsError(f"Restore destination exists: {destination}")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent))
    try:
        shutil.copytree(archive, staging, dirs_exist_ok=True)
        config_path = staging / "state/config.json"
        config = json.loads(config_path.read_text())
        with closing(sqlite3.connect(staging / "state/memory.db")) as connection, connection:
            for name, project in config["projects"].items():
                relative = contained(staging, staging / project["path"]).relative_to(staging)
                project["path"] = str(destination / relative)
                connection.execute("UPDATE project SET path=? WHERE name=?", (project["path"], name))
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        validate_notes(staging, destination=destination)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
