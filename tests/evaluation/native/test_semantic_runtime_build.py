import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import basic_memory
import pytest

from shared_memory.runtime_build import BUILD_REVISION, PATCH_ARGS, PROJECT_CREATE_PATCH, package_wheel, verify


def synthetic_wheel(tmp_path: Path) -> Path:
    stage = tmp_path / "stage"
    shutil.copytree(
        Path(basic_memory.__file__).parent,
        stage / "basic_memory",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    if "enable_mcp_project_create" in (stage / "basic_memory/mcp/tools/projects.py").read_text():
        subprocess.run(
            [*PATCH_ARGS, "-i", str(PROJECT_CREATE_PATCH), "--reverse"], cwd=stage, check=True, capture_output=True
        )
    info = stage / "basic_memory-1.0.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.4\nName: basic-memory\nVersion: 1.0.0\n")
    (info / "WHEEL").write_text("Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    (info / "RECORD").write_text(f"{info.name}/RECORD,,\n")
    wheel = tmp_path / "basic_memory-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(stage).as_posix())
    return wheel


def test_build_is_reproducible_and_applies_patch(tmp_path: Path) -> None:
    wheel = synthetic_wheel(tmp_path)
    first, manifest = package_wheel(wheel, tmp_path / "one", "1.0.0", None)
    second, second_manifest = package_wheel(wheel, tmp_path / "two", "1.0.0", None)

    assert first.read_bytes() == second.read_bytes()
    assert manifest == second_manifest
    assert json.loads((tmp_path / "one/manifest.json").read_text()) == manifest
    assert manifest["wheel_version"] == f"1.0.0+{BUILD_REVISION}"
    assert manifest["project_create_patch_sha256"] == hashlib.sha256(PROJECT_CREATE_PATCH.read_bytes()).hexdigest()

    with zipfile.ZipFile(first) as archive, zipfile.ZipFile(wheel) as source:
        info = f"basic_memory-1.0.0+{BUILD_REVISION}.dist-info"
        assert f"Version: 1.0.0+{BUILD_REVISION}" in archive.read(f"{info}/METADATA").decode()
        assert f"{info}/RECORD" in archive.namelist()
        project_tools = "basic_memory/mcp/tools/projects.py"
        config = "basic_memory/config_models.py"
        package_files = {path for path in source.namelist() if path.startswith("basic_memory/")}
        assert package_files == {path for path in archive.namelist() if path.startswith("basic_memory/")}
        changed = {path for path in package_files if archive.read(path) != source.read(path)}
        assert changed == set(manifest["patched_files"]) == {config, project_tools}
        assert "enable_mcp_project_create" in archive.read(project_tools).decode()
        assert "semantic_search_enabled" not in archive.read(config).decode()


def test_verify_rejects_wheel_that_does_not_match_manifest(tmp_path: Path) -> None:
    wheel = synthetic_wheel(tmp_path)
    with pytest.raises(ValueError, match="built wheel hash mismatch"):
        verify(wheel, f"1.0.0+{BUILD_REVISION}", "0" * 64)
