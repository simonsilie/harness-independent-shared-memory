"""Install the approval gate launcher into a Codex or OpenCode configuration."""

import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import sys
import tomllib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("bm_project", "bm_search", "bm_read", "bm_write")
PERMISSIONS = [
    {"action": "basic_memory_*", "resource": "*", "effect": "deny"},
    *({"action": f"basic_memory_{tool}", "resource": "*", "effect": "allow"} for tool in TOOLS),
]


class InstallError(ValueError):
    """The installation cannot be planned safely."""


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    index = start
    quote = ""
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise InstallError(f"Unterminated {opening!r} at offset {start}")


def _mask(text: str, *, mask_trailing_commas: bool = True) -> str:
    """Blank JSONC comments and trailing commas while keeping every offset."""
    result = list(text)
    index = 0
    quoted = False
    previous = -1
    while index < len(text):
        char = text[index]
        if quoted:
            if char == "\\":
                index += 2
                continue
            if char == '"':
                quoted = False
                previous = index
            index += 1
            continue
        if char == '"':
            quoted = True
        elif text.startswith("//", index):
            end = text.find("\n", index)
            end = len(text) if end == -1 else end
            result[index:end] = " " * (end - index)
            index = end
            continue
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = len(text) if end == -1 else end + 2
            result[index:end] = " " * (end - index)
            index = end
            continue
        elif not char.isspace():
            if mask_trailing_commas and char in "}]" and previous >= 0 and text[previous] == ",":
                result[previous] = " "
            previous = index
        index += 1
    return "".join(result)


def _value_end(masked: str, start: int, end: int) -> int:
    if masked[start] in "[{":
        opening = masked[start]
        return _matching(masked, start, opening, "]" if opening == "[" else "}")
    if masked[start] == '"':
        index = start + 1
        while index < end:
            if masked[index] == "\\":
                index += 2
                continue
            if masked[index] == '"':
                return index + 1
            index += 1
        raise InstallError("Unterminated string in client configuration")
    index = start
    while index < end and masked[index] not in ",}]" and masked[index] not in "\r\n":
        index += 1
    return index


def _member(masked: str, start: int, end: int, key: str) -> tuple[int, int, int] | None:
    """Return the key, value start and value end offsets of a direct object member."""
    member = None
    index = start + 1
    depth = 0
    while index < end:
        if masked[index] == '"':
            stop = index + 1
            while stop < end:
                if masked[stop] == "\\":
                    stop += 2
                    continue
                if masked[stop] == '"':
                    break
                stop += 1
            if depth == 0:
                colon = stop + 1
                while colon < end and masked[colon] in " \t\r\n":
                    colon += 1
                if colon < end and masked[colon] == ":" and json.loads(masked[index : stop + 1]) == key:
                    if member is not None:
                        raise InstallError(f"Duplicate OpenCode setting {key!r}")
                    value = colon + 1
                    while value < end and masked[value] in " \t\r\n":
                        value += 1
                    member = index, value, _value_end(masked, value, end)
            index = stop + 1
            continue
        if masked[index] in "[{":
            depth += 1
        elif masked[index] in "]}":
            depth -= 1
        index += 1
    return member


def _indent(text: str, position: int) -> str:
    line = text.rfind("\n", 0, position) + 1
    match = re.match(r"[ \t]*", text[line:position])
    return match.group(0) if match else ""


def _insert(masked: str, text: str, start: int, end: int, snippets: list[str]) -> str:
    empty = not masked[start + 1 : end].strip()
    previous = end - 1
    while previous > start and masked[previous].isspace():
        previous -= 1
    pieces = []
    for index, snippet in enumerate(snippets):
        comma = "" if index == 0 and (empty or masked[previous] == ",") else ","
        pieces.append(f"{comma}\n{_indent(text, start)}  {snippet}")
    return "".join(pieces)


def _server(uv: str, arguments: list[str]) -> dict[str, Any]:
    return {"type": "local", "command": [uv, *arguments], "codemode": False}


def plan_jsonc(original: str, uv: str, arguments: list[str]) -> str:
    if not original.strip():
        return (
            json.dumps(
                {
                    "mcp": {"servers": {"basic_memory": _server(uv, arguments)}},
                    "permissions": PERMISSIONS,
                },
                indent=2,
            )
            + "\n"
        )
    masked = _mask(original, mask_trailing_commas=False)
    try:
        document = json.loads(_mask(masked))
    except json.JSONDecodeError as error:
        raise InstallError(f"Invalid JSON/JSONC client configuration: {error}") from error
    if not isinstance(document, dict) or not masked.strip().startswith("{"):
        raise InstallError("Expected a JSON/JSONC object for the OpenCode configuration")

    root_start = masked.index("{")
    root_end = _matching(masked, root_start, "{", "}")
    edits: list[tuple[int, int, str]] = []
    insertions: dict[tuple[int, int], list[str]] = {}

    def insert(start: int, end: int, snippet: str) -> None:
        insertions.setdefault((start, end), []).append(snippet)

    mcp = _member(masked, root_start, root_end, "mcp")
    if mcp is None:
        insert(
            root_start,
            root_end,
            json.dumps("mcp") + ": " + json.dumps({"servers": {"basic_memory": _server(uv, arguments)}}),
        )
    else:
        _, mcp_value, mcp_end = mcp
        if masked[mcp_value] != "{":
            raise InstallError("Expected the OpenCode 'mcp' setting to be an object")
        servers = _member(masked, mcp_value, mcp_end, "servers")
        if servers is None:
            insert(
                mcp_value, mcp_end, json.dumps("servers") + ": " + json.dumps({"basic_memory": _server(uv, arguments)})
            )
        else:
            _, servers_value, servers_end = servers
            if masked[servers_value] != "{":
                raise InstallError("Expected the OpenCode 'mcp.servers' setting to be an object")
            entry = _member(masked, servers_value, servers_end, "basic_memory")
            if entry is None:
                insert(
                    servers_value, servers_end, json.dumps("basic_memory") + ": " + json.dumps(_server(uv, arguments))
                )
            else:
                _, entry_value, entry_end = entry
                if masked[entry_value] != "{":
                    raise InstallError("Expected the OpenCode 'basic_memory' entry to be an object")
                if document["mcp"]["servers"]["basic_memory"].get("type") != "local":
                    raise InstallError("Only local OpenCode 'basic_memory' entries can be migrated")
                command = _member(masked, entry_value, entry_end, "command")
                replacement = json.dumps([uv, *arguments])
                if command is None:
                    insert(entry_value, entry_end, json.dumps("command") + ": " + replacement)
                else:
                    edits.append((command[1], command[2] + 1, replacement))

    permissions = _member(masked, root_start, root_end, "permissions")
    if permissions is None:
        insert(root_start, root_end, json.dumps("permissions") + ": " + json.dumps(PERMISSIONS))
    else:
        _, value, _ = permissions
        if masked[value] != "[":
            raise InstallError("Expected the OpenCode 'permissions' setting to be an array")
        existing = document.get("permissions") or []
        present = {json.dumps(rule, sort_keys=True) for rule in existing if isinstance(rule, dict)}
        missing = [rule for rule in PERMISSIONS if json.dumps(rule, sort_keys=True) not in present]
        if missing:
            # OpenCode uses the last matching rule, so existing policies take precedence.
            indent = _indent(original, value) + "  "
            defaults = f",\n{indent}".join(json.dumps(rule) for rule in missing)
            separator = "," if existing else ""
            edits.append((value + 1, value + 1, f"\n{indent}{defaults}{separator}"))

    for (start, end), snippets in insertions.items():
        edits.append((end, end, _insert(masked, original, start, end, snippets)))
    for start, end, replacement in sorted(edits, key=lambda edit: edit[0], reverse=True):
        original = original[:start] + replacement + original[end:]
    return original


def _toml_assign(block: str, key: str, value: str | list[str]) -> str:
    rendered = json.dumps(value)
    token = re.escape(key)
    for match in re.finditer(rf"""(?m)^[ \t]*(?:{token}|"{token}"|'{token}')[ \t]*=[ \t]*""", block):
        # An unparseable prefix means the apparent assignment is inside another value.
        try:
            tomllib.loads(block[: match.start()])
        except tomllib.TOMLDecodeError:
            continue
        start = match.end()
        for boundary in re.finditer(r"#|\n|\Z", block[start:]):
            end = start + boundary.start()
            assignment = block[match.start() : end]
            try:
                parsed = tomllib.loads(assignment)
            except tomllib.TOMLDecodeError:
                continue
            if isinstance(value, list):
                # Removing a real comment leaves the parsed argument values unchanged.
                comments = []
                previous_end = 0
                for marker in re.finditer("#", assignment):
                    offset = marker.start()
                    if offset < previous_end:
                        continue
                    line_end = assignment.find("\n", offset)
                    line_end = len(assignment) if line_end == -1 else line_end
                    try:
                        without_comment = tomllib.loads(assignment[:offset] + assignment[line_end:])
                    except tomllib.TOMLDecodeError:
                        continue
                    if without_comment == parsed:
                        comments.append(assignment[offset:line_end])
                        previous_end = line_end
                if comments:
                    indent = _indent(block, start)
                    comment_lines = "".join(f"{indent}  {comment}\n" for comment in comments)
                    rendered = f"[\n{comment_lines}{indent}  {rendered[1:-1]}\n{indent}]"
            end = start + len(block[start:end].rstrip(" \t"))
            return block[:start] + rendered + block[end:]
        raise InstallError(f"Invalid TOML value for {key!r}")

    separator = "" if block.endswith("\n") else "\n"
    return block + f"{separator}{key} = {rendered}\n"


def plan_toml(original: str, uv: str, arguments: list[str]) -> str:
    try:
        servers = tomllib.loads(original).get("mcp_servers", {})
    except tomllib.TOMLDecodeError as error:
        raise InstallError(f"Invalid TOML client configuration: {error}") from error
    if isinstance(servers, dict):
        existing = servers.get("basic_memory")
        if isinstance(existing, dict) and "url" in existing:
            raise InstallError("Only stdio Codex 'basic_memory' entries can be migrated")

    headers = re.finditer(r"(?m)^[ \t]*\[.*\][ \t]*(?:#[^\r\n]*)?$", original)
    match = None
    end = len(original)
    for header in headers:
        try:
            table = tomllib.loads(header.group())
            tomllib.loads(original[: header.start()])
        except tomllib.TOMLDecodeError:
            continue
        if match is not None:
            end = header.start()
            break
        if table == {"mcp_servers": {"basic_memory": {}}}:
            match = header
    if match is None:
        block = (
            "[mcp_servers.basic_memory]\n"
            f"command = {json.dumps(uv)}\n"
            f"args = {json.dumps(arguments)}\n"
            f"enabled_tools = {json.dumps(list(TOOLS))}\n"
        )
        separator = (
            "" if not original else ("" if original.endswith("\n\n") else "\n" if original.endswith("\n") else "\n\n")
        )
        return original + separator + block
    block = original[match.start() : end]
    block = _toml_assign(_toml_assign(block, "command", uv), "args", arguments)
    return original[: match.start()] + block + original[end:]


def check_runtime(root: Path, uv: str | None) -> str:
    for name in (".venv/bin/python", ".venv/bin/basic-memory"):
        if not os.access(root / name, os.X_OK):
            raise InstallError(
                f"Runtime missing at {root}. Set it up first, then run the installer again:\n"
                f"  cd {shlex.quote(str(root))} && uv sync --locked"
            )
    if uv is None:
        raise InstallError("uv is required; install it, then set up the runtime with 'uv sync --locked'")
    return str(Path(uv).absolute())


def make_plan(
    client: str, client_config: Path, gate_config: Path, root: Path | None = None, uv: str | None = None
) -> tuple[str, str]:
    root = ROOT if root is None else root
    uv = check_runtime(root, uv)
    from .config import load_config

    try:
        config = load_config(gate_config)
    except (OSError, ValueError) as error:
        raise InstallError(f"Invalid approval gate configuration {gate_config}: {error}") from error
    executable = config.native_command[0]
    configured_path = (config.env or {}).get("PATH")
    if not executable or (
        (Path(executable).is_absolute() or configured_path is not None)
        and shutil.which(executable, path=configured_path) is None
    ):
        raise InstallError(f"Native executable from {gate_config} is missing or not executable: {executable!r}")
    arguments = [
        "run",
        "--directory",
        str(root),
        "--locked",
        "--no-sync",
        "python",
        "-m",
        "approval_gate.proxy",
        "--config",
        str(gate_config.resolve()),
    ]
    original = client_config.read_text() if client_config.exists() else ""
    if client == "codex":
        updated = plan_toml(original, uv, arguments)
    else:
        updated = plan_jsonc(original, uv, arguments)
    try:
        tomllib.loads(updated) if client == "codex" else json.loads(_mask(updated))
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as error:
        raise InstallError(f"Refusing to write invalid client configuration: {error}") from error
    return original, updated


def write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content.encode())
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "opencode"), required=True)
    parser.add_argument("--client-config", type=Path, required=True, help="client configuration to update")
    parser.add_argument("--config", type=Path, required=True, help="approval gate JSON configuration")
    parser.add_argument("--apply", action="store_true", help="write the planned change (default: preview only)")
    args = parser.parse_args(argv)

    try:
        client_config = args.client_config.expanduser().resolve()
        original, updated = make_plan(args.client, client_config, args.config.expanduser(), uv=shutil.which("uv"))
    except InstallError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Could not prepare the installation: {error}", file=sys.stderr)
        return 1

    if original == updated:
        print(f"No changes needed in {args.client_config}.")
        return 0
    sys.stdout.writelines(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{args.client_config}",
            tofile=f"b/{args.client_config}",
        )
    )
    if not args.apply:
        print("Preview only; repeat with --apply to write this change.")
        return 0
    try:
        write_config(client_config, updated)
    except OSError as error:
        print(f"Could not write {args.client_config}: {error}", file=sys.stderr)
        return 1
    print(f"Updated {args.client_config}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
