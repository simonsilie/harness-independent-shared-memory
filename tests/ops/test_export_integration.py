"""Independent export check with synthetic notes, runnable from a fresh checkout."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlite_vec
import yaml

from ops import export

PERSONAL = "personal"
ALPHA = "alpha"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.name.startswith(("memory.db", "basic-memory.log", "watch-status"))
    }


def sql_dump(db: Path) -> str:
    connection = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        return "\n".join(connection.iterdump())
    finally:
        connection.close()


def test_sql_dump_handles_vector_tables_read_only(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    connection = sqlite3.connect(db)
    try:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        connection.execute("CREATE VIRTUAL TABLE embeddings USING vec0(embedding float[2])")
        connection.execute("INSERT INTO embeddings(rowid, embedding) VALUES (1, '[1.0, 2.0]')")
        connection.commit()
    finally:
        connection.close()
    before = db.read_bytes()

    dump = sql_dump(db)

    assert "USING vec0(embedding float[2])" in dump
    assert 'INSERT INTO "embeddings" VALUES(1,' in dump
    assert sql_dump(db) == dump
    assert db.read_bytes() == before


def reindex(root: Path) -> None:
    config = json.loads((root / "state/config.json").read_text())
    home = root / Path(config["projects"][config["default_project"]]["path"])
    env = os.environ | {
        "BASIC_MEMORY_CONFIG_DIR": str(root / "state"),
        "BASIC_MEMORY_HOME": str(home),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "HF_HUB_OFFLINE": "1",
    }
    executable = Path(sys.executable).with_name("basic-memory")
    subprocess.run([str(executable), "reindex", "--full", "--search"], env=env, check=True, capture_output=True)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / "store"
    state = root / "state"
    personal = root / "notes/personal"
    alpha = root / "notes/projects/alpha"
    for folder in (state, personal / "durable", personal / "temporary", alpha / "durable", alpha / "temporary"):
        folder.mkdir(parents=True)

    now = datetime.now(timezone.utc).replace(microsecond=0)

    def stamp(days: int) -> str:
        return (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    notes = {
        personal / "durable/preferences.md": (
            "---\ntitle: Shared preference\ntype: note\npermalink: personal/durable/preferences\n"
            "kind: durable\nstatus: active\n---\n\nShared preference body.\n"
        ),
        personal / "temporary/active-handover.md": (
            "---\ntitle: Active personal handover\ntype: note\npermalink: personal/temporary/active-handover\n"
            f"kind: temporary\nstatus: active\nlast_activity: '{stamp(-1)}'\n---\n\nResume this work.\n"
        ),
        alpha / "durable/decision.md": (
            "---\ntitle: Alpha decision\ntype: note\npermalink: alpha/durable/decision\n"
            "kind: durable\nstatus: active\ntags:\n- alpha\n---\n\nAlpha project decision.\n"
        ),
        alpha / "temporary/expired-handover.md": (
            "---\ntitle: Expired alpha handover\ntype: note\npermalink: alpha/temporary/expired-handover\n"
            f"kind: temporary\nstatus: active\nlast_activity: '{stamp(-8)}'\n---\n\nOld alpha work.\n"
        ),
        alpha / "temporary/archived-handover.md": (
            "---\ntitle: Archived alpha handover\ntype: note\npermalink: alpha/temporary/archived-handover\n"
            f"kind: temporary\nstatus: archived\nlast_activity: '{stamp(-2)}'\narchive_reason: completed\n"
            f"completed_at: '{stamp(-2)}'\narchived_at: '{stamp(-2)}'\n---\n\nFinished alpha work.\n"
        ),
    }
    for path, body in notes.items():
        path.write_text(body)
    config = {
        "projects": {
            PERSONAL: {"path": str(personal), "mode": "local"},
            ALPHA: {"path": str(alpha), "mode": "local"},
        },
        "default_project": PERSONAL,
        "database_backend": "sqlite",
        "database_url": None,
        "default_search_type": "text",
        "semantic_search_enabled": False,
        "auto_update": False,
        "logfire_enabled": False,
    }
    (state / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    reindex(root)
    return root


def parse_bundle(bundle: Path) -> dict[str, dict]:
    notes = {}
    for path in sorted(bundle.rglob("*.md")):
        relative = path.relative_to(bundle)
        if relative.name in {"index.md", "log.md"}:
            continue
        _, header, body = path.read_text().split("---\n", 2)
        notes[str(relative)] = {"meta": yaml.safe_load(header), "body": body.strip("\n")}
    return notes


def activity(meta: dict) -> datetime:
    return datetime.fromisoformat(meta["last_activity"].replace("Z", "+00:00"))


READER_SCRIPT = """
import json
import sys
from pathlib import Path

import yaml


class BlockBasicMemory:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "basic_memory" or fullname.startswith("basic_memory."):
            raise ModuleNotFoundError(fullname)
        return None


sys.meta_path.insert(0, BlockBasicMemory())


def parse(bundle):
    notes = {}
    for path in sorted(bundle.rglob("*.md")):
        relative = path.relative_to(bundle)
        if relative.name in {"index.md", "log.md"}:
            continue
        _, header, body = path.read_text().split("---\\n", 2)
        notes[str(relative)] = {"meta": yaml.safe_load(header), "body": body.strip("\\n")}
    return notes


def search(bundle, query):
    return [
        relative
        for relative, note in parse(bundle).items()
        if query.lower() in note["body"].lower() or query.lower() in str(note["meta"]).lower()
    ]


bundles = Path(sys.argv[1])
print(json.dumps({
    "personal_preference": search(bundles / "personal", "Shared preference"),
    "alpha_preference": search(bundles / "alpha", "Shared preference"),
    "alpha_archive": search(bundles / "alpha", "archive_reason"),
    "titles": sorted(note["meta"]["title"] for note in parse(bundles / "personal").values()),
    "basic_memory_loaded": "basic_memory" in sys.modules,
}))
"""


def test_export_covers_all_projects_and_is_readable_without_basic_memory(store: Path, tmp_path: Path) -> None:
    before_files = inventory(store)
    before_dump = sql_dump(store / "state/memory.db")
    destination = tmp_path / "export"

    assert export(store, destination) == destination

    assert inventory(store) == before_files
    assert sql_dump(store / "state/memory.db") == before_dump
    bundles = {path.name: path for path in (destination / "bundles").iterdir()}
    assert set(bundles) == {PERSONAL, ALPHA}
    for name, bundle in bundles.items():
        index = yaml.safe_load((bundle / "index.md").read_text().split("---\n")[1])
        assert index["okf_version"] == "0.2"

    exported = {name: parse_bundle(bundle) for name, bundle in bundles.items()}
    assert set(exported[PERSONAL]) == {"durable/preferences.md", "temporary/active-handover.md"}
    assert set(exported[ALPHA]) == {
        "durable/decision.md",
        "temporary/expired-handover.md",
        "temporary/archived-handover.md",
    }
    config = json.loads((store / "state/config.json").read_text())
    for name, notes in exported.items():
        project_root = store / Path(config["projects"][name]["path"])
        for relative, note in notes.items():
            _, header, body = (project_root / relative).read_text().split("---\n", 2)
            assert note["body"] == body.strip("\n")
            assert all(note["meta"].get(key) == value for key, value in yaml.safe_load(header).items())
            assert note["meta"]["permalink"].startswith(name + "/")
            assert note["meta"]["bm"]["okf_export"]["version"] == 1

    temporary = [n for notes in exported.values() for n in notes.values() if n["meta"].get("kind") == "temporary"]
    active = [n for n in temporary if n["meta"]["status"] == "active"]
    archived = [n for n in temporary if n["meta"]["status"] == "archived"]
    now = datetime.now(timezone.utc)
    assert [n["meta"]["title"] for n in active if activity(n["meta"]) >= now - timedelta(days=7)] == [
        "Active personal handover"
    ]
    assert [n["meta"]["title"] for n in active if activity(n["meta"]) < now - timedelta(days=7)] == [
        "Expired alpha handover"
    ]
    assert [n["meta"]["title"] for n in archived] == ["Archived alpha handover"]
    assert all({"archive_reason", "completed_at", "archived_at"} <= set(n["meta"]) for n in archived)

    reader = tmp_path / "reader.py"
    reader.write_text(READER_SCRIPT)
    output = subprocess.run(
        [sys.executable, str(reader), str(destination / "bundles")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(output.stdout) == {
        "personal_preference": ["durable/preferences.md"],
        "alpha_preference": [],
        "alpha_archive": ["temporary/archived-handover.md"],
        "titles": ["Active personal handover", "Shared preference"],
        "basic_memory_loaded": False,
    }


def test_export_cli_writes_bundles_for_every_project(store: Path, tmp_path: Path) -> None:
    destination = tmp_path / "cli-export"
    result = subprocess.run(
        [sys.executable, "-m", "ops", "export", str(store), str(destination)],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip().splitlines()[-1] == str(destination)
    assert {path.name for path in (destination / "bundles").iterdir()} == {PERSONAL, ALPHA}


def test_export_refuses_existing_destination(store: Path, tmp_path: Path) -> None:
    destination = tmp_path / "export"
    destination.mkdir()

    with pytest.raises(FileExistsError):
        export(store, destination)
