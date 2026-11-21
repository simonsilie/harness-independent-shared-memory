import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ops import backup, inventory, recovery, restore


@pytest.fixture
def store(tmp_path):
    source = tmp_path / "live"
    (source / "state").mkdir(parents=True)
    (source / "notes/personal").mkdir(parents=True)
    (source / "observations").mkdir()
    (source / "observations/observations.jsonl").write_text('{"continuation":"partial"}\n')
    (source / "state/.bmignore").write_text("*.tmp\n")
    config = {
        "projects": {"personal": {"path": str(source / "notes/personal"), "mode": "local"}},
        "database_backend": "sqlite",
        "database_url": None,
        "semantic_search_enabled": False,
    }
    (source / "state/config.json").write_text(json.dumps(config))
    with sqlite3.connect(source / "state/memory.db") as connection:
        connection.execute("CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, path TEXT)")
        connection.execute("INSERT INTO project VALUES (1, ?, ?)", ("personal", str(source / "notes/personal")))
        connection.execute(
            "CREATE TABLE note_content (project_id INTEGER, file_path TEXT, markdown_content TEXT, db_checksum TEXT)"
        )
        for status in ["active", "archived"]:
            body = f"---\nkind: temporary\nstatus: {status}\n---\nPending recovery work\n"
            (source / f"notes/personal/{status}.md").write_text(body)
            connection.execute(
                "INSERT INTO note_content VALUES (1, ?, ?, ?)",
                (f"{status}.md", body, hashlib.sha256(body.encode()).hexdigest()),
            )
    return source


def test_round_trip_preserves_content_and_live_store(store, tmp_path):
    before = inventory(store)
    archive, target = tmp_path / "backup", tmp_path / "restored"

    backup(store, archive)
    restore(archive, target)

    assert inventory(store) == before
    for relative in [
        "notes/personal/active.md",
        "notes/personal/archived.md",
        "observations/observations.jsonl",
        "state/.bmignore",
    ]:
        assert (target / relative).read_bytes() == (store / relative).read_bytes()
    with sqlite3.connect(target / "state/memory.db") as connection:
        assert connection.execute("SELECT path FROM project").fetchone()[0] == str(target / "notes/personal")
        assert connection.execute("SELECT count(*) FROM note_content").fetchone()[0] == 2


def test_backup_refuses_unindexed_file(store, tmp_path):
    (store / "notes/personal/missing.md").write_text("Unsaved knowledge")

    with pytest.raises(ValueError, match="Unindexed"):
        backup(store, tmp_path / "backup")

    assert not (tmp_path / "backup/manifest.json").exists()


def test_restore_refuses_corruption(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    (archive / "notes/personal/active.md").write_text("Corrupted")

    with pytest.raises(ValueError, match="manifest mismatch"):
        restore(archive, tmp_path / "restore")

    assert not (tmp_path / "restore").exists()


def test_restore_refuses_existing_destination(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    before = inventory(store)

    with pytest.raises(FileExistsError):
        restore(archive, store)

    assert inventory(store) == before


def test_wal_snapshot_remains_reusable_after_reads(store, tmp_path):
    archive = tmp_path / "backup"
    with sqlite3.connect(store / "state/memory.db") as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE wal_evidence (value TEXT)")
        connection.execute("INSERT INTO wal_evidence VALUES ('committed in WAL')")
        connection.commit()

        backup(store, archive)
        before = inventory(archive)
        restore(archive, tmp_path / "first")
        restore(archive, tmp_path / "second")

        assert inventory(archive) == before
        assert not list((archive / "state").glob("memory.db-*"))
        with sqlite3.connect(tmp_path / "second/state/memory.db") as recovered:
            assert recovered.execute("SELECT value FROM wal_evidence").fetchone()[0] == "committed in WAL"


def test_backup_with_unexpected_sidecar_can_be_retried(store, tmp_path, monkeypatch):
    archive = tmp_path / "backup"
    before = inventory(store)

    validate = recovery.validate_notes

    def leave_sidecar(root):
        validate(root)
        (root / "state/memory.db-shm").touch()

    with monkeypatch.context() as patch:
        patch.setattr(recovery, "validate_notes", leave_sidecar)
        with pytest.raises(ValueError, match=r"memory\.db-shm"):
            backup(store, archive)

    assert not archive.exists()
    assert not list(tmp_path.glob(f".{archive.name}.*.tmp"))
    assert inventory(store) == before

    backup(store, archive)
    assert (archive / "manifest.json").exists()
    assert inventory(store) == before


def test_failed_restore_leaves_no_destination_and_can_be_retried(store, tmp_path, monkeypatch):
    archive = tmp_path / "backup"
    backup(store, archive)
    target = tmp_path / "restored"
    before = inventory(archive)

    def interrupt_publication(staging, destination):
        assert destination == target and not target.exists()
        expected = str(target / "notes/personal")
        config = json.loads((staging / "state/config.json").read_text())
        assert config["projects"]["personal"]["path"] == expected
        with closing(sqlite3.connect(staging / "state/memory.db")) as connection:
            assert connection.execute("SELECT path FROM project").fetchone()[0] == expected
        raise OSError("interrupted before publication")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rename", interrupt_publication)
        with pytest.raises(OSError, match="interrupted before publication"):
            restore(archive, target)

    assert not target.exists()
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))
    assert inventory(archive) == before

    restore(archive, target)
    assert (target / "manifest.json").exists()
    with sqlite3.connect(target / "state/memory.db") as connection:
        assert connection.execute("SELECT path FROM project").fetchone()[0] == str(target / "notes/personal")
