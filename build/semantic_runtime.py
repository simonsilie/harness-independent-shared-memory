"""Build a pinned, patched Basic Memory wheel and check it in a fresh environment."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "basic-memory-semantic-disable.patch"
LOCK = ROOT / "uv.lock"
WATCHER = ROOT / "evaluation" / "native" / "mcp_watcher.py"
DIST = ROOT / "build" / "dist"
VERIFY_ENV = ROOT / "build" / ".verify-venv"
BUILD_REVISION = "semantic.1"
PATCH_ARGS = ["patch", "--batch", "--force", "--fuzz=0", "-p1", "-i", str(PATCH)]
WHEEL_SUFFIX = "-py3-none-any.whl"


def load_pin() -> tuple[str, str, str]:
    """Return the Basic Memory version, wheel URL and wheel hash recorded in uv.lock."""
    lock = tomllib.loads(LOCK.read_text())
    package = next((item for item in lock["package"] if item["name"] == "basic-memory"), None)
    if package is None:
        raise ValueError(f"basic-memory is not pinned in {LOCK}")
    wheels = [item for item in package["wheels"] if item["url"].endswith(WHEEL_SUFFIX)]
    if len(wheels) != 1:
        raise ValueError(f"expected one pure-Python wheel for basic-memory in {LOCK}, found {len(wheels)}")
    wheel = wheels[0]
    return package["version"], wheel["url"], wheel["hash"].removeprefix("sha256:")


def download(url: str, expected_sha256: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"pinned wheel hash mismatch: expected {expected_sha256}, got {actual}")
    return data


def patched_files() -> list[str]:
    files = [line.removeprefix("--- a/") for line in PATCH.read_text().splitlines() if line.startswith("--- a/")]
    if len(files) != 7:
        raise ValueError(f"expected seven patched source files, found {len(files)}")
    return files


def apply_patch(root: Path) -> None:
    existing = subprocess.run([*PATCH_ARGS, "--reverse", "--dry-run"], cwd=root, capture_output=True, text=True)
    if existing.returncode == 0:
        raise ValueError("the pinned wheel already contains the semantic-disable patch")
    applied = subprocess.run(PATCH_ARGS, cwd=root, capture_output=True, text=True)
    if applied.returncode != 0:
        raise RuntimeError(f"could not apply the semantic-disable patch: {applied.stderr or applied.stdout}")
    reversed_check = subprocess.run([*PATCH_ARGS, "--reverse", "--dry-run"], cwd=root, capture_output=True, text=True)
    if reversed_check.returncode != 0:
        raise RuntimeError(f"the applied patch could not be verified: {reversed_check.stderr or reversed_check.stdout}")


def reversion(root: Path, base_version: str, build_version: str) -> None:
    source_info = root / f"basic_memory-{base_version}.dist-info"
    info = root / f"basic_memory-{build_version}.dist-info"
    source_info.rename(info)
    metadata = info / "METADATA"
    text = metadata.read_text()
    if f"Version: {base_version}\n" not in text:
        raise ValueError(f"pinned wheel metadata does not declare Version: {base_version}")
    metadata.write_text(text.replace(f"Version: {base_version}\n", f"Version: {build_version}\n", 1))

    record = info / "RECORD"
    lines = []
    for path in sorted(path for path in root.rglob("*") if path.is_file() and path != record):
        digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip("=")
        lines.append(f"{path.relative_to(root).as_posix()},sha256={digest},{path.stat().st_size}")
    lines.append(f"{info.name}/RECORD,,")
    record.write_text("\n".join(lines) + "\n")


def pack(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(path for path in root.rglob("*") if path.is_file()):
            entry = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, path.read_bytes())


def package_wheel(source: Path, out_dir: Path, base_version: str, expected_sha256: str | None) -> tuple[Path, dict]:
    """Repack a pinned wheel with the patch applied under a distinct build version."""
    data = source.read_bytes()
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(f"pinned wheel hash mismatch: expected {expected_sha256}, got {actual_sha256}")

    build_version = f"{base_version}+{BUILD_REVISION}"
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / f"basic_memory-{build_version}{WHEEL_SUFFIX}"
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(source) as archive:
            for member in archive.namelist():
                if member.startswith("/") or ".." in Path(member).parts:
                    raise ValueError(f"unsafe wheel member: {member}")
            archive.extractall(root)
        apply_patch(root)
        reversion(root, base_version, build_version)
        pack(root, destination)

    manifest = {
        "base_version": base_version,
        "base_wheel_sha256": actual_sha256,
        "build_revision": BUILD_REVISION,
        "patch_sha256": hashlib.sha256(PATCH.read_bytes()).hexdigest(),
        "patched_files": patched_files(),
        "wheel": destination.name,
        "wheel_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "wheel_version": build_version,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return destination, manifest


def build(out_dir: Path, local_wheel: Path | None) -> tuple[Path, dict]:
    version, url, wheel_hash = load_pin()
    with TemporaryDirectory() as temporary:
        source = Path(temporary) / "pinned.whl"
        source.write_bytes(local_wheel.read_bytes() if local_wheel else download(url, wheel_hash))
        return package_wheel(source, out_dir, version, wheel_hash)


def verify(wheel: Path, build_version: str, expected_sha256: str) -> subprocess.CompletedProcess:
    """Install the built wheel into a fresh environment and run the existing watcher check."""
    actual_sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"built wheel hash mismatch: expected {expected_sha256}, got {actual_sha256}")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the fresh-environment check")
    if VERIFY_ENV.exists():
        shutil.rmtree(VERIFY_ENV)
    python = ROOT / ".venv" / "bin" / "python"
    interpreter = str(python) if python.is_file() else sys.executable
    subprocess.run([uv, "venv", "--python", interpreter, str(VERIFY_ENV)], check=True)

    uv_env = os.environ | {"UV_CACHE_DIR": str(ROOT / ".uv-cache")}
    with TemporaryDirectory() as temporary:
        requirements = Path(temporary) / "requirements.txt"
        exported = subprocess.run(
            [uv, "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes", "--format", "requirements-txt"],
            cwd=ROOT,
            env=uv_env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        kept = [line for line in exported.splitlines() if not line.startswith("basic-memory==")]
        requirements.write_text("\n".join([*kept, str(wheel)]) + "\n")
        subprocess.run(
            [uv, "pip", "install", "--python", str(VERIFY_ENV / "bin" / "python"), "-r", str(requirements)],
            cwd=ROOT,
            env=uv_env,
            check=True,
        )

    watcher_env = os.environ | {
        "PHASE1B_EXPECTED_VERSION": build_version,
        "WATCHFILES_FORCE_POLLING": "true",
    }
    return subprocess.run(
        [str(VERIFY_ENV / "bin" / "python"), str(WATCHER), "--installed-semantic-disabled"],
        cwd=ROOT,
        env=watcher_env,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build", help="build the patched wheel from the uv lock pin")
    build_command.add_argument("--out", type=Path, default=DIST)
    build_command.add_argument("--wheel", type=Path, help="local copy of the pinned wheel; still hash-checked")
    verify_command = commands.add_parser("verify", help="check the built wheel in a fresh environment")
    verify_command.add_argument("--out", type=Path, default=DIST)
    args = parser.parse_args(argv)

    if args.command == "build":
        _, manifest = build(args.out, args.wheel)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    manifest = json.loads((args.out / "manifest.json").read_text())
    result = verify(args.out / manifest["wheel"], manifest["wheel_version"], manifest["wheel_sha256"])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
