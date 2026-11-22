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
from contextlib import ExitStack
from pathlib import Path
from stat import S_IMODE
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
JSON_STRING = r'"(?:[^"\\]|\\.)*"'
JSON_COMMENT = r"//[^\r\n]*|/\*[\s\S]*?\*/"
JSONC = re.compile(rf"({JSON_STRING})|{JSON_COMMENT}|,(?=(?:\s|{JSON_COMMENT})*[\]}}])")
TOML_COMMAND = re.compile(rf"(?m)^[ \t]*command[ \t]*=[ \t]*({JSON_STRING}|'[^'\r\n]*')")


def plan_switch(path: Path, old: str, new: str) -> tuple[str, str, str]:
    original = path.read_bytes().decode()
    replacement = json.dumps(new, ensure_ascii=False)
    executable = new
    if path.suffix in {".json", ".jsonc"}:
        # Keep original offsets so the replacement preserves formatting and comments.
        document = JSONC.sub(lambda match: match[1] or re.sub(r"[^\r\n]", " ", match[0]), original)
        parse = json.loads
        expected = parse(document)
        mcp = expected.get("mcp", {}) if isinstance(expected, dict) else {}
        entries = mcp.get("servers", mcp) if isinstance(mcp, dict) else {}
        servers = [
            server
            for server in (entries.values() if isinstance(entries, dict) else ())
            if isinstance(server, dict) and server.get("command") in ([old], [new])
        ]
        candidates = (match.span() for match in re.finditer(JSON_STRING, document) if parse(match[0]) == old)
        old_command, new_command = [old], [new]
        executable = re.sub(r"\{env:([^{}]+)\}", lambda match: os.environ.get(match[1], ""), executable)
    else:
        document = original
        parse = tomllib.loads
        expected = parse(document)
        entries = expected.get("mcp_servers", {})
        servers = [
            server
            for server in (entries.values() if isinstance(entries, dict) else ())
            if isinstance(server, dict) and server.get("command") in (old, new) and not server.get("args")
        ]
        candidates = (
            match.span(1)
            for match in TOML_COMMAND.finditer(document)
            if parse(f"command = {match[1]}")["command"] == old
        )
        old_command, new_command = old, new
    if len(servers) != 1:
        raise ValueError(f"{path}: expected exactly one matching MCP server without arguments")
    resolved = shutil.which(executable)
    if not resolved or ("/" in executable and not Path(executable).is_absolute()):
        raise ValueError(f"{path}: replacement launcher is not executable: {new!r}")
    launcher = str(Path(resolved).absolute())
    if servers[0]["command"] == old_command and old != new:
        servers[0]["command"] = new_command
        for start, end in candidates:
            if parse(document[:start] + replacement + document[end:]) == expected:
                return original, original[:start] + replacement + original[end:], launcher
        raise ValueError(f"{path}: could not locate the matching MCP server's command")
    return original, original, launcher


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
        changes = {}
        launchers = set()
        for filename, old, new in args.replace_launcher:
            path = Path(filename).expanduser().resolve(strict=True)
            if path == config or path in changes:
                raise ValueError(f"{path}: expected a distinct client configuration")
            original, updated, executable = plan_switch(path, old, new)
            changes[path] = original, updated
            launchers.add(executable)
            if args.dry_run and original != updated:
                print(f"Switch launcher in {path} from {old!r} to {new!r}")

        if args.test or changes:
            commands.insert(1, [str(python), "-c", "import pytest"])
            commands.append(
                [
                    "/usr/bin/env",
                    f"SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS={json.dumps(sorted(launchers))}",
                    str(python),
                    "-m",
                    "pytest",
                    "-q",
                    "tests/approval_gate/test_native_integration.py",
                ]
            )
        for command in commands:
            if args.dry_run:
                print(shlex.join(command))
            else:
                subprocess.run(command, cwd=ROOT, check=True)

        if args.dry_run:
            return 0
        with ExitStack() as cleanup:
            staged = {}
            for path, (original, updated) in changes.items():
                if original != updated:
                    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                        temporary = Path(stream.name)
                        cleanup.callback(temporary.unlink, missing_ok=True)
                        stream.write(updated.encode())
                    temporary.chmod(S_IMODE(path.stat().st_mode))
                    staged[path] = temporary
            for path, (original, _) in changes.items():
                if path.read_bytes().decode() != original:
                    raise ValueError(f"{path}: configuration changed during installation")
            for path in changes:
                if path in staged:
                    staged[path].replace(path)
                    print(f"Switched launcher in {path}")
                else:
                    print(f"Launcher already configured in {path}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
