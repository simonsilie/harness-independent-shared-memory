import os
import shutil
import subprocess
import sys
from pathlib import Path

import basic_memory
import pytest

from shared_memory.runtime_build import PROJECT_CREATE_PATCH, apply_patch

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module", params=["unpatched", "patched"])
def patched_package(tmp_path_factory, request):
    directory = tmp_path_factory.mktemp("semantic-disable")
    shutil.copytree(
        Path(basic_memory.__file__).parent,
        directory / "basic_memory",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    patch_args = [
        "patch",
        "--batch",
        "--force",
        "--fuzz=0",
        "-p1",
        "-i",
        str(ROOT / "patches/basic-memory-semantic-disable.patch"),
    ]
    source_is_patched = "semantic_search_enabled: bool" in (directory / "basic_memory/config_models.py").read_text()
    if source_is_patched != (request.param == "patched"):
        subprocess.run(
            [*patch_args, *(["--reverse"] if source_is_patched else [])],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
    already_applied = (
        subprocess.run(
            [*patch_args, "--reverse", "--dry-run"], cwd=directory, capture_output=True, text=True
        ).returncode
        == 0
    )
    if not already_applied:
        subprocess.run(patch_args, cwd=directory, capture_output=True, text=True, check=True)
    return directory


def test_disabled_configuration_skips_semantic_stack(patched_package):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from basic_memory.config import BasicMemoryConfig, DatabaseBackend
from basic_memory.repository import search_repository as factory
from basic_memory.repository import sqlite_search_repository as sqlite
from basic_memory.repository import postgres_search_repository as postgres
from basic_memory.repository import semantic_runtime
from basic_memory.repository.search_scope import ProjectScope
from basic_memory.repository.semantic_errors import SemanticSearchDisabledError
from basic_memory.mcp.tools import search

assert BasicMemoryConfig().semantic_search_enabled is True
os.environ["BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED"] = "false"
assert BasicMemoryConfig().semantic_search_enabled is False
os.environ.pop("BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED")
config = BasicMemoryConfig(
    semantic_search_enabled=False,
    semantic_embedding_provider="invalid-disabled-provider",
    default_search_type="hybrid",
    reranker_enabled=True,
    reranker_provider="invalid-disabled-provider",
)
assert BasicMemoryConfig.model_validate_json(config.model_dump_json()).semantic_search_enabled is False
with patch.object(semantic_runtime, "sqlite_vector_runtime_available", side_effect=AssertionError("vector probe")):
    assert not semantic_runtime.semantic_runtime_available(config)
    assert not semantic_runtime.semantic_runtime_available(config.model_copy(update={"database_backend": DatabaseBackend.POSTGRES}))
with patch.object(search, "get_container", return_value=SimpleNamespace(config=config)):
    assert search._default_search_type(["main"]) == "text"

async def check():
    for module in (factory, sqlite, postgres):
        for name in ("create_embedding_provider", "create_rerank_provider", "create_semantic_vector_index"):
            if hasattr(module, name):
                setattr(module, name, Mock(side_effect=AssertionError(name)))
    for backend, repository_type in ((DatabaseBackend.SQLITE, sqlite.SQLiteSearchRepository), (DatabaseBackend.POSTGRES, postgres.PostgresSearchRepository)):
        settings = config.model_copy(update={"database_backend": backend})
        repository = factory.create_search_repository(None, 1, settings)
        assert isinstance(repository, repository_type)
        assert not await repository.semantic_effectively_enabled()
        assert repository._embedding_provider is None
        assert repository._rerank_provider is None
        assert not repository._vector_tables_initialized
        for ids in ([], [1, 2]):
            result = await repository.sync_entity_vectors_batch(ids)
            assert result.entities_skipped == len(ids)
            assert result.entities_failed == result.entities_synced == 0
        try:
            repository._assert_semantic_available()
        except SemanticSearchDisabledError:
            pass
        else:
            raise AssertionError("semantic query should be refused")
        direct = repository_type(None, 1, settings, embedding_provider=object(), rerank_provider=object())
        assert direct._embedding_provider is direct._rerank_provider is None
        reader = factory.create_search_reader(None, ProjectScope.single(1), settings)
        assert reader.semantic is None
    factory.create_embedding_provider.reset_mock()
    try:
        factory.create_search_repository(None, 1, BasicMemoryConfig(semantic_search_enabled=True))
    except AssertionError as error:
        assert str(error) == "create_embedding_provider"
    else:
        raise AssertionError("enabled mode should construct its provider")
    factory.create_embedding_provider.assert_called_once()

asyncio.run(check())
""",
        ],
        cwd=patched_package,
        env={key: value for key, value in os.environ.items() if not key.startswith("BASIC_MEMORY_")}
        | {"PYTHONPATH": str(patched_package), "BASIC_MEMORY_CONFIG_DIR": str(patched_package / "state")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("opt_in", ["default", "environment", "config"])
def test_mcp_project_creation_requires_opt_in(patched_package, tmp_path, opt_in):
    projects = patched_package / "basic_memory/mcp/tools/projects.py"
    if "enable_mcp_project_create" not in projects.read_text():
        apply_patch(patched_package, PROJECT_CREATE_PATCH)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import json
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.exceptions import ToolError

from basic_memory.config import ConfigManager
from basic_memory.mcp.server import mcp
import basic_memory.mcp.tools.projects

opt_in = sys.argv[1]
state = Path(os.environ["BASIC_MEMORY_CONFIG_DIR"])
state.mkdir()
root = state.parent / "main"
root.mkdir()
target = state.parent / "new-project"
(state / "config.json").write_text(json.dumps({
    "projects": {"main": {"path": str(root), "mode": "local"}},
    "default_project": "main",
    "semantic_search_enabled": False,
    **({"enable_mcp_project_create": True} if opt_in == "config" else {}),
}))

async def check():
    args = {"command": "create", "name": "new-project", "path": str(target), "set_default": True}
    async with Client(mcp) as client:
        await client.call_tool("bm_project", {"command": "list"})
        await client.call_tool("bm_project", {"command": "recent", "project": "main"})
        if opt_in == "default":
            try:
                await client.call_tool("bm_project", args)
            except ToolError:
                pass
            else:
                raise AssertionError("MCP project creation should require an opt-in")
            assert not target.exists()
            config = ConfigManager().config
            assert set(config.projects) == {"main"}
            assert config.default_project == "main"
        else:
            await client.call_tool("bm_project", args)
            assert target.is_dir()
            assert "new-project" in ConfigManager().config.projects
            assert ConfigManager().config.default_project == "new-project"

asyncio.run(check())
""",
            opt_in,
        ],
        cwd=patched_package,
        env={key: value for key, value in os.environ.items() if not key.startswith("BASIC_MEMORY_")}
        | {
            "PYTHONPATH": str(patched_package),
            "BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "state"),
            "BASIC_MEMORY_HOME": str(tmp_path / "main"),
            "BASIC_MEMORY_FORCE_LOCAL": "true",
            "FASTMCP_CHECK_FOR_UPDATES": "off",
        }
        | ({"BASIC_MEMORY_ENABLE_MCP_PROJECT_CREATE": "true"} if opt_in == "environment" else {}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
