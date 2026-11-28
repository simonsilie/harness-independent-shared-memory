import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from shared_memory.ops import backup, inventory, recovery, restore


@pytest.fixture
def note_suffix():
    return ".md"


@pytest.fixture
def store(tmp_path, note_suffix):
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
            filename = f"{status}{note_suffix}"
            (source / "notes/personal" / filename).write_text(body)
            connection.execute(
                "INSERT INTO note_content VALUES (1, ?, ?, ?)",
                (filename, body, hashlib.sha256(body.encode()).hexdigest()),
            )
    return source


@pytest.mark.parametrize("note_suffix", [".md", ".markdown", ".MARKDOWN"])
def test_round_trip_preserves_content_and_live_store(store, tmp_path, note_suffix):
    before = inventory(store)
    archive, target = tmp_path / "backup", tmp_path / "restored"

    backup(store, archive)
    restore(archive, target)

    assert inventory(store) == before
    for relative in [
        f"notes/personal/active{note_suffix}",
        f"notes/personal/archived{note_suffix}",
        "observations/observations.jsonl",
        "state/.bmignore",
    ]:
        assert (target / relative).read_bytes() == (store / relative).read_bytes()
    with sqlite3.connect(target / "state/memory.db") as connection:
        assert connection.execute("SELECT path FROM project").fetchone()[0] == str(target / "notes/personal")
        assert connection.execute("SELECT count(*) FROM note_content").fetchone()[0] == 2


@pytest.mark.parametrize("missing_suffix", [".md", ".markdown"])
def test_backup_refuses_unindexed_file(store, tmp_path, missing_suffix):
    (store / f"notes/personal/missing{missing_suffix}").write_text("Unsaved knowledge")

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


def test_empty_project_survives_round_trip(store, tmp_path):
    empty = store / "notes/empty"
    empty.mkdir()
    config_path = store / "state/config.json"
    config = json.loads(config_path.read_text())
    config["projects"]["empty"] = {"path": str(empty), "mode": "local"}
    config_path.write_text(json.dumps(config))
    with sqlite3.connect(store / "state/memory.db") as connection:
        connection.execute("INSERT INTO project VALUES (2, 'empty', ?)", (str(empty),))
    before = inventory(store)

    archive = tmp_path / "backup"
    target = tmp_path / "restored"
    backup(store, archive)
    restore(archive, target)

    assert inventory(store) == before
    assert (archive / "notes/empty").is_dir()
    assert (target / "notes/empty").is_dir()
    with sqlite3.connect(target / "state/memory.db") as connection:
        assert {row[0] for row in connection.execute("SELECT name FROM project")} == {"personal", "empty"}


def test_restore_refuses_missing_empty_project_root(store, tmp_path):
    empty = store / "notes/empty"
    empty.mkdir()
    config_path = store / "state/config.json"
    config = json.loads(config_path.read_text())
    config["projects"]["empty"] = {"path": str(empty), "mode": "local"}
    config_path.write_text(json.dumps(config))
    with sqlite3.connect(store / "state/memory.db") as connection:
        connection.execute("INSERT INTO project VALUES (2, 'empty', ?)", (str(empty),))

    archive = tmp_path / "backup"
    backup(store, archive)
    expected = hashlib.sha256((archive / "manifest.json").read_bytes()).hexdigest()
    (archive / "notes/empty").rmdir()

    with pytest.raises(ValueError, match="Missing project root"):
        restore(archive, tmp_path / "restore", expected_manifest_digest=expected)

    assert not (tmp_path / "restore").exists()


def test_restore_refuses_symlink_swapped_before_open(store, tmp_path, monkeypatch):
    archive = tmp_path / "backup"
    backup(store, archive)
    victim = archive / "notes/personal/active.md"
    real_open = os.open
    swapped = False

    def swap_then_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and path == "active.md" and kwargs.get("dir_fd") is not None:
            swapped = True
            victim.unlink()
            victim.symlink_to(archive / "outside")
        return real_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", swap_then_open)
        with pytest.raises(ValueError, match="Link or special file"):
            restore(archive, tmp_path / "restore")

    assert swapped
    assert not (tmp_path / "restore").exists()


def test_restore_refuses_file_symlink(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    (archive / "notes/personal/active.md").unlink()
    (archive / "notes/personal/active.md").symlink_to(store / "notes/personal/active.md")
    before = inventory(store)

    with pytest.raises(ValueError, match="Link or special file"):
        restore(archive, tmp_path / "restore")

    assert not (tmp_path / "restore").exists()
    assert not list(tmp_path.glob(".restore.*.tmp"))
    assert inventory(store) == before


def test_restore_does_not_follow_directory_symlink(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("outside content")
    (archive / "notes/personal/leak").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="Link or special file"):
        restore(archive, tmp_path / "restore")

    assert not (tmp_path / "restore").exists()
    assert not (tmp_path / "restore/notes/personal/leak/secret.md").exists()
    assert not list(tmp_path.glob(".restore.*.tmp"))


def test_restore_refuses_special_file(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    os.mkfifo(archive / "notes/personal/pipe")

    with pytest.raises(ValueError, match="Link or special file"):
        restore(archive, tmp_path / "restore")

    assert not (tmp_path / "restore").exists()


def test_restore_verifies_manifest_on_staging_copy(store, tmp_path, monkeypatch):
    archive = tmp_path / "backup"
    backup(store, archive)
    before = inventory(archive)
    original_copy_file = recovery._copy_file

    def tamper(fd, target):
        original_copy_file(fd, target)
        if target.name == "active.md":
            target.write_bytes(target.read_bytes() + b"tampered")

    with monkeypatch.context() as patch:
        patch.setattr(recovery, "_copy_file", tamper)
        with pytest.raises(ValueError, match="manifest mismatch"):
            restore(archive, tmp_path / "restore")

    assert not (tmp_path / "restore").exists()
    assert not list(tmp_path.glob(".restore.*.tmp"))
    assert inventory(archive) == before


def test_restore_optional_manifest_digest(store, tmp_path):
    archive = tmp_path / "backup"
    backup(store, archive)
    expected = hashlib.sha256((archive / "manifest.json").read_bytes()).hexdigest()

    restore(archive, tmp_path / "matching", expected_manifest_digest=expected)
    assert (tmp_path / "matching/manifest.json").exists()

    with pytest.raises(ValueError, match="Manifest digest mismatch"):
        restore(archive, tmp_path / "wrong", expected_manifest_digest="0" * 64)
    assert not (tmp_path / "wrong").exists()


def test_cli_restore_accepts_expected_manifest_digest(store, tmp_path, monkeypatch):
    from shared_memory.ops.__main__ import main

    archive = tmp_path / "backup"
    backup(store, archive)
    expected = hashlib.sha256((archive / "manifest.json").read_bytes()).hexdigest()
    target = tmp_path / "restored"
    monkeypatch.setattr(
        "sys.argv",
        ["ops", "restore", str(archive), str(target), "--expected-manifest-digest", expected],
    )
    original_umask = os.umask(0o077)
    try:
        main()
    finally:
        os.umask(original_umask)

    assert (target / "manifest.json").exists()
