"""Contract tests for the Basic Memory internals the approval gate relies on.

A failure here after a Basic Memory upgrade names the internal that changed;
adjust `shared_memory.approval_gate.basic_memory_api` before trusting the gate again.
"""

from importlib.metadata import version
from pathlib import Path

import pytest

from shared_memory.approval_gate.basic_memory_api import (
    RUNTIME_MARKDOWN_FILE_SUFFIXES,
    ParseError,
    ProjectById,
    coerce_dict,
    generate_permalink,
    has_frontmatter,
    memory_url_path,
    parse_frontmatter,
    parse_project,
    resolve_path_within_root,
    split_project_permalink_prefix,
    valid_project_path_value,
)

PROJECT_ID = "0a8e7f0e-6b2c-4d0f-9b1a-3c2d1e0f9a8b"


def test_pinned_basic_memory_version() -> None:
    # Bump together with pyproject.toml after rerunning this module against the new release.
    assert version("basic-memory") == "1.0.0"


def test_frontmatter_parsing() -> None:
    note = "---\nkind: temporary\nstatus: active\n---\nbody"
    assert has_frontmatter(note)
    assert parse_frontmatter(note) == {"kind": "temporary", "status": "active"}
    assert not has_frontmatter("--- not a fence")
    assert not has_frontmatter("---\nkind: temporary\n")
    with pytest.raises(ParseError):
        parse_frontmatter("---\n: [\n---\n")


def test_coerce_dict_decodes_only_json_objects() -> None:
    assert coerce_dict('{"kind": "temporary"}') == {"kind": "temporary"}
    assert coerce_dict("[1]") == "[1]"
    assert coerce_dict(None) is None


def test_parse_project_classifies_uuid_and_name() -> None:
    assert parse_project(f" {PROJECT_ID.upper()} ") == ProjectById(PROJECT_ID)
    assert not isinstance(parse_project("Main Notes"), ProjectById)


def test_generate_permalink() -> None:
    assert generate_permalink("Team/Main Notes") == "team/main-notes"


def test_split_project_permalink_prefix_prefers_longest_match() -> None:
    permalinks = {"research", "research/2026"}
    assert split_project_permalink_prefix("research/2026/temporary/a.md", permalinks) == (
        "research/2026",
        "temporary/a.md",
    )
    assert split_project_permalink_prefix("other/a.md", permalinks) is None


def test_memory_url_path() -> None:
    assert memory_url_path("memory://temporary/a") == "temporary/a"
    assert memory_url_path("temporary/a") == "temporary/a"


def test_markdown_suffixes() -> None:
    assert RUNTIME_MARKDOWN_FILE_SUFFIXES == {".md", ".markdown"}


def test_valid_project_path_value_rejects_traversal() -> None:
    assert valid_project_path_value("temporary/a..md")
    assert not valid_project_path_value("temporary/../a.md")
    assert not valid_project_path_value("~/a.md")


def test_resolve_path_within_root(tmp_path: Path) -> None:
    assert resolve_path_within_root("temporary/a.md", tmp_path) == tmp_path.resolve() / "temporary/a.md"
    assert resolve_path_within_root(".", tmp_path) == tmp_path.resolve()
    with pytest.raises(ValueError):
        resolve_path_within_root(".", tmp_path, allow_root=False)
    with pytest.raises(ValueError):
        resolve_path_within_root("../a.md", tmp_path)
