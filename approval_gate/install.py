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
from tempfile import NamedTemporaryFile, TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
JSON_STRING = r'"(?:[^"\\]|\\.)*"'
JSON_COMMENT = r"//[^\r\n]*|/\*[\s\S]*?\*/"
JSONC = re.compile(rf"({JSON_STRING})|{JSON_COMMENT}|,(?=(?:\s|{JSON_COMMENT})*[\]}}])")
TOML_COMMAND = re.compile(rf"(?m)^[ \t]*command[ \t]*=[ \t]*({JSON_STRING}|'[^'\r\n]*')")


def plan_switch(path: Path, old: str, new: str) -> tuple[str, str, dict]:
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
        env_key = "environment"
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
        env_key = "env"
    if len(servers) != 1:
        raise ValueError(f"{path}: expected exactly one matching MCP server without arguments")
    server = servers[0]
    environment = server.get(env_key, {})
    if not isinstance(environment, dict) or not all(isinstance(value, str) for value in environment.values()):
        raise ValueError(f"{path}: expected string values for MCP server environment")
    resolved = shutil.which(executable, path=environment.get("PATH"))
    if not resolved or ("/" in executable and not Path(executable).is_absolute()):
        raise ValueError(f"{path}: replacement launcher is not executable: {new!r}")
    launcher = {"command": str(Path(resolved).absolute()), "env": environment}
    if env_key == "env" and server.get("cwd"):
        launcher["cwd"] = server["cwd"]
    if server["command"] == old_command and old != new:
        server["command"] = new_command
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
        "--wheel",
        type=Path,
        help="install a prebuilt Basic Memory wheel alongside the gate dependencies (implies --test)",
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
        check_config = [
            str(python),
            "-c",
            "from approval_gate.config import load_config; from pathlib import Path; "
            "import shutil, sys; native = load_config(Path(sys.argv[1])).native_command[0]; "
            "sys.exit(None if shutil.which(native) else f'Native launcher is not executable: {native}')",
            str(config),
        ]
        install = [uv, "pip", "install", "--python", str(python), "--no-deps"]
        changes = {}
        launchers = []
        for filename, old, new in args.replace_launcher:
            path = Path(filename).expanduser().resolve(strict=True)
            if path == config or path in changes:
                raise ValueError(f"{path}: expected a distinct client configuration")
            original, updated, launcher = plan_switch(path, old, new)
            changes[path] = original, updated
            if launcher not in launchers:
                launchers.append(launcher)
            if args.dry_run and original != updated:
                print(f"Switch launcher in {path} from {old!r} to {new!r}")

        with ExitStack() as cleanup:
            staging = Path("<staging>") if args.dry_run else Path(cleanup.enter_context(TemporaryDirectory()))
            target = staging / "packages"
            packages_to_install = pins.copy()
            if wheel:
                candidate = staging / wheel.name
                if not args.dry_run:
                    # Use the same bytes even if the original wheel is rebuilt during validation.
                    shutil.copyfile(wheel, candidate)
                packages_to_install.append(str(candidate))
            env = {
                "PYTHONPATH": os.pathsep.join(filter(None, (str(target), os.environ.get("PYTHONPATH")))),
            }
            if wheel:
                env["SHARED_MEMORY_APPROVAL_TEST_NATIVE"] = str(target / "bin/basic-memory")

            def run(command: list[str], overrides: dict[str, str] | None = None) -> None:
                if args.dry_run:
                    assignments = [
                        f"{key}={value if key != 'SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS' else '<client launchers>'}"
                        for key, value in (overrides or {}).items()
                    ]
                    print(shlex.join([*(["env", *assignments] if assignments else []), *command]))
                else:
                    subprocess.run(command, cwd=ROOT, check=True, env=os.environ | overrides if overrides else None)

            run(check_config)
            run_tests = args.test or bool(changes) or wheel is not None
            if run_tests:
                run([str(python), "-c", "import pytest"])
            run([*install, "--target", str(target), *packages_to_install])
            run([str(python), "-m", "approval_gate.proxy", "--help"], env)
            if run_tests:
                run(
                    [str(python), "-m", "pytest", "-q", "tests/approval_gate/test_native_integration.py"],
                    env
                    | {
                        "SHARED_MEMORY_APPROVAL_TEST_LAUNCHERS": json.dumps(launchers),
                        "SHARED_MEMORY_APPROVAL_CHECK_CONFIG": str(config),
                    },
                )
            if args.dry_run:
                run([*install, *packages_to_install])
                return 0
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
            run([*install, *packages_to_install])
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
