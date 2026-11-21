"""Install the approval gate into an existing Basic Memory environment."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from stat import S_IMODE
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
COMMAND = re.compile(r'(?m)^[ \t]*(?:"command"[ \t]*:\s*(\[\s*)|command[ \t]*=\s*)("(?:[^"\\\n]|\\.)*")')


def plan_switch(path: Path, old: str, new: str) -> tuple[str, str]:
    original = path.read_bytes().decode()
    old_value, new_value = old, new
    old, new = (json.dumps(value, ensure_ascii=False) for value in (old, new))
    matches = [
        match
        for match in COMMAND.finditer(original)
        if match[2] in (old, new) and (not match[1] or original[match.end() :].lstrip().startswith("]"))
    ]
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one matching single-executable command, found {len(matches)}")
    start, end = matches[0].span(2)
    updated = original[:start] + new + original[end:]
    if not matches[0][1]:
        expected = tomllib.loads(original)
        servers = [
            server
            for server in expected.get("mcp_servers", {}).values()
            if server.get("command") in (old_value, new_value)
        ]
        if len(servers) != 1 or servers[0].get("args"):
            raise ValueError(f"{path}: expected exactly one matching MCP server without arguments")
        servers[0]["command"] = new_value
        if tomllib.loads(updated) != expected:
            raise ValueError(f"{path}: replacement must only change the matching MCP server's command")
    return original, updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", type=Path, default=ROOT / ".venv/bin/python", help="existing environment interpreter"
    )
    parser.add_argument("--config", type=Path, required=True, help="existing approval-gate JSON configuration")
    parser.add_argument(
        "--wheel", type=Path, help="install a prebuilt Basic Memory wheel alongside the gate dependencies"
    )
    parser.add_argument("--test", action="store_true", help="run the native integration tests (requires pytest)")
    parser.add_argument("--dry-run", action="store_true", help="show the commands and configuration changes")
    parser.add_argument(
        "--replace-launcher",
        nargs=3,
        action="append",
        default=[],
        metavar=("FILE", "OLD", "NEW"),
        help="switch one existing, argument-free TOML or JSON/JSONC command (repeatable, implies --test)",
    )
    args = parser.parse_args()

    try:
        # Resolving a venv's Python symlink would select its base interpreter.
        python = args.python.expanduser().absolute()
        if not os.access(python, os.X_OK) or not os.access(python.with_name("basic-memory"), os.X_OK):
            raise ValueError(f"{python}: expected an existing environment with an executable basic-memory")
        config = args.config.expanduser().resolve(strict=True)
        wheel = args.wheel.expanduser().resolve(strict=True) if args.wheel else None
        if wheel and (not wheel.is_file() or wheel.suffix != ".whl"):
            raise ValueError(f"{wheel}: expected a wheel file")
        uv = shutil.which("uv")
        if uv is None:
            raise ValueError("uv is required to install the gate dependencies")
        packages = tomllib.loads((ROOT / "uv.lock").read_text())["package"]
        pins = [
            f"{package['name']}=={package['version']}"
            for package in packages
            if package["name"] in {"configargparse", "loguru"}
        ]
        commands = [
            [
                str(python),
                "-c",
                "from approval_gate.config import load_config; from pathlib import Path; "
                "import shutil, sys; native = load_config(Path(sys.argv[1])).native_command[0]; "
                "sys.exit(None if shutil.which(native) else f'Native launcher is not executable: {native}')",
                str(config),
            ],
            [uv, "pip", "install", "--python", str(python), "--no-deps", *pins, *([str(wheel)] if wheel else [])],
            [str(python), "-m", "approval_gate.proxy", "--help"],
        ]
        if args.test or args.replace_launcher:
            commands.insert(1, [str(python), "-c", "import pytest"])
            commands.append([str(python), "-m", "pytest", "-q", "tests/approval_gate/test_native_integration.py"])

        changes = {}
        for filename, old, new in args.replace_launcher:
            path = Path(filename).expanduser().resolve(strict=True)
            if path == config or path in changes:
                raise ValueError(f"{path}: expected a distinct client configuration")
            changes[path] = plan_switch(path, old, new)
            if args.dry_run and changes[path][0] != changes[path][1]:
                print(f"Switch launcher in {path} from {old!r} to {new!r}")

        for command in commands:
            if args.dry_run:
                print(shlex.join(command))
            else:
                subprocess.run(command, cwd=ROOT, check=True)

        for path, (original, updated) in changes.items():
            if args.dry_run:
                continue
            if original == updated:
                print(f"Launcher already configured in {path}")
                continue
            if path.read_bytes().decode() != original:
                raise ValueError(f"{path}: configuration changed during installation")
            with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    stream.write(updated.encode())
                    stream.close()
                    temporary.chmod(S_IMODE(path.stat().st_mode))
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
            print(f"Switched launcher in {path}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
