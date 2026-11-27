"""Same-version backup and isolated restore of a local Basic Memory store."""

import errno
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
from collections.abc import Callable
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from basic_memory.runtime.storage import runtime_file_path_is_markdown_note


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


_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def _open_entry(parent_fd: int, name: str, path: Path) -> tuple[bool, int]:
    """Open a child relative to its parent directory, refusing links and special files."""
    try:
        fd = os.open(name, _OPEN_FLAGS, dir_fd=parent_fd)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ValueError(f"Link or special file in store: {path}") from error
        raise
    mode = os.fstat(fd).st_mode
    if stat.S_ISDIR(mode):
        return True, fd
    if stat.S_ISREG(mode):
        return False, fd
    os.close(fd)
    raise ValueError(f"Link or special file in store: {path}")


@contextmanager
def _closing_fd(fd: int):
    try:
        yield fd
    finally:
        os.close(fd)


def _walk(root: Path, on_directory: Callable[[Path], None], on_file: Callable[[Path, int], None]) -> None:
    """Traverse root through directory descriptors; callbacks get paths relative to root."""
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with _closing_fd(root_fd):
        _walk_fd(root_fd, Path(), on_directory, on_file)


def _walk_fd(
    dir_fd: int, prefix: Path, on_directory: Callable[[Path], None], on_file: Callable[[Path, int], None]
) -> None:
    with os.scandir(dir_fd) as entries:
        names = sorted(entry.name for entry in entries)
    for name in names:
        path = prefix / name
        is_directory, fd = _open_entry(dir_fd, name, path)
        with _closing_fd(fd):
            if is_directory:
                on_directory(path)
                _walk_fd(fd, path, on_directory, on_file)
            else:
                on_file(path, fd)


def _read_all(fd: int) -> bytes:
    chunks = []
    while chunk := os.read(fd, 1024 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def inventory(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}

    def record(relative: Path, fd: int) -> None:
        files[str(relative)] = hashlib.sha256(_read_all(fd)).hexdigest()

    _walk(root, lambda _: None, record)
    return files


def _copy_file(fd: int, target: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    with os.fdopen(os.open(target, flags, 0o600), "wb") as stream:
        while chunk := os.read(fd, 1024 * 1024):
            stream.write(chunk)


def _copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    _walk(
        source,
        lambda relative: (destination / relative).mkdir(mode=0o700, parents=True, exist_ok=True),
        lambda relative, fd: _copy_file(fd, destination / relative),
    )


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
            if not project_root.is_dir():
                raise ValueError(f"Missing project root: {project_root}")
            notes = connection.execute("SELECT * FROM note_content WHERE project_id=?", (project["id"],)).fetchall()
            for note in notes:
                path = contained(project_root, project_root / note["file_path"])
                if digest(path) != note["db_checksum"] or path.read_bytes() != note["markdown_content"].encode():
                    raise ValueError(f"File/database mismatch: {path}")
            markdown_paths = {
                path.relative_to(project_root).as_posix()
                for path in project_root.rglob("*")
                if runtime_file_path_is_markdown_note(path.name) and path.is_file()
            }
            if markdown_paths != {note["file_path"] for note in notes}:
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
            _copy_tree(path, staging / relative)
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


def restore(archive: Path, destination: Path, *, expected_manifest_digest: str | None = None) -> None:
    """Restore a backup, optionally checking manifest.json against a digest held in a trusted store.

    Nothing in the archive is trusted until it has been copied into a private staging
    directory and the complete manifest has been verified there.
    """
    archive, destination = archive.resolve(), destination.resolve()
    if destination.is_relative_to(archive) or archive.is_relative_to(destination):
        raise ValueError("Restore must be separate from the backup")
    if destination.exists():
        raise FileExistsError(f"Restore destination exists: {destination}")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent))
    try:
        # Copy before verifying: the archive may change underneath us or be on mutable
        # storage. Refusing links and special files here also stops copytree from
        # pulling content from outside the archive via directory symlinks.
        _copy_tree(archive, staging)
        manifest_bytes = (staging / "manifest.json").read_bytes()
        if (
            expected_manifest_digest is not None
            and hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_digest
        ):
            raise ValueError("Manifest digest mismatch")
        manifest = json.loads(manifest_bytes)
        actual = inventory(staging)
        del actual["manifest.json"]
        if actual != manifest["files"]:
            raise ValueError("Backup manifest mismatch")
        validate_notes(staging)
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
