"""Print a client configuration snippet for the approval gate."""

import argparse
import json
import shutil
import tomllib
from pathlib import Path

from . import ALLOWED_TOOLS

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "opencode"), required=True)
    parser.add_argument("--config", type=Path, required=True, help="path to the approval gate JSON configuration")
    args = parser.parse_args(argv)

    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv was not found on PATH")
    command = str(Path(uv).absolute())
    checkout = str(ROOT)
    config = str(args.config.expanduser().resolve())
    arguments = [
        "run",
        "--directory",
        checkout,
        "--locked",
        "--no-sync",
        "python",
        "-m",
        "approval_gate.proxy",
        "--config",
        config,
    ]
    if args.client == "codex":
        for label, path in (("uv executable", command), ("checkout", checkout), ("gate configuration", config)):
            if any(ord(character) > 0xFFFF for character in path):
                parser.error(
                    f"the {label} path contains a character outside the Basic Multilingual Plane; "
                    "use a path without emoji or other characters above U+FFFF for the Codex snippet"
                )
        snippet = "\n".join(
            (
                "[mcp_servers.basic_memory]",
                f"command = {json.dumps(command)}",
                f"args = {json.dumps(arguments)}",
                f"enabled_tools = {json.dumps(ALLOWED_TOOLS)}",
            )
        )
        try:
            tomllib.loads(snippet)
        except tomllib.TOMLDecodeError as error:
            parser.error(f"could not render the Codex configuration: {error}")
    else:
        server = {"type": "local", "command": [command, *arguments], "codemode": False}
        permissions = [
            {"action": "basic_memory_*", "resource": "*", "effect": "deny"},
            *({"action": f"basic_memory_{tool}", "resource": "*", "effect": "allow"} for tool in ALLOWED_TOOLS),
        ]
        snippet = json.dumps({"mcp": {"servers": {"basic_memory": server}}, "permissions": permissions}, indent=2)
    print(snippet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
