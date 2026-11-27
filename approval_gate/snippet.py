"""Print a client configuration snippet for the approval gate."""

import argparse
import json
import shutil
import tomllib
from pathlib import Path

from . import ALLOWED_TOOLS

ROOT = Path(__file__).resolve().parents[1]


def render_snippet(client: str, command: Path, checkout: Path, config: Path) -> str:
    arguments = [
        "run",
        "--directory",
        str(checkout),
        "--locked",
        "--no-sync",
        "shared-memory-approval-gate",
        "--config",
        str(config),
    ]
    if client == "codex":
        snippet = "\n".join(
            (
                "[mcp_servers.basic_memory]",
                f"command = {json.dumps(str(command), ensure_ascii=False)}",
                f"args = {json.dumps(arguments, ensure_ascii=False)}",
                f"enabled_tools = {json.dumps(ALLOWED_TOOLS)}",
            )
        ).replace("\x7f", r"\u007f")
        tomllib.loads(snippet)
        return snippet

    server = {"type": "local", "command": [str(command), *arguments], "codemode": False}
    permissions = [
        {"action": "basic_memory_*", "resource": "*", "effect": "deny"},
        *({"action": f"basic_memory_{tool}", "resource": "*", "effect": "allow"} for tool in ALLOWED_TOOLS),
    ]
    return json.dumps({"mcp": {"servers": {"basic_memory": server}}, "permissions": permissions}, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "opencode"), required=True)
    parser.add_argument("--config", type=Path, required=True, help="path to the approval gate JSON configuration")
    args = parser.parse_args(argv)

    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv was not found on PATH")
    try:
        snippet = render_snippet(args.client, Path(uv).absolute(), ROOT, args.config.expanduser().resolve())
    except tomllib.TOMLDecodeError as error:
        parser.error(f"could not render the Codex configuration: {error}")
    print(snippet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
