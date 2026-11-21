"""Write validation and eligibility for automatic temporary writes."""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from basic_memory.file_utils import ParseError, has_frontmatter, parse_frontmatter
from basic_memory.mcp.project_context_identifiers import split_project_permalink_prefix
from basic_memory.mcp.tool_params import ProjectById, parse_project
from basic_memory.runtime.storage import RUNTIME_MARKDOWN_FILE_SUFFIXES
from basic_memory.schemas.memory import memory_url_path
from basic_memory.utils import coerce_dict, generate_permalink, resolve_path_within_root, valid_project_path_value

from . import ProposalError

type NativeCall = Callable[[str, dict[str, Any]], dict[str, Any]]


def effective_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
    content = arguments.get("content")
    if not isinstance(content, str):
        raise ProposalError("A write requires string content.")
    try:
        fields = parse_frontmatter(content) if has_frontmatter(content) else {}
    except ParseError as error:
        raise ProposalError(f"Malformed note frontmatter: {error}") from error
    metadata = coerce_dict(arguments.get("metadata"))
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ProposalError("Write metadata must be an object.")
        fields.update(metadata)
    return fields


def valid_last_activity(value: Any) -> bool:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return False
    else:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def write_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    checksum = arguments.get("expected_checksum")
    overwrite = arguments.get("overwrite")
    if checksum is not None:
        if not isinstance(checksum, str) or not checksum.strip() or overwrite is False:
            raise ProposalError("Replacing a note requires its expected_checksum and permits overwrite.")
        if overwrite is not None and overwrite is not True:
            raise ProposalError("overwrite must be a boolean.")
        return dict(arguments)
    if overwrite is not None and overwrite is not False:
        raise ProposalError("Replacing a note requires its expected_checksum.")
    return {**arguments, "overwrite": False}


def pin_durable_target(arguments: dict[str, Any], call_native: NativeCall) -> tuple[str, dict[str, Any]]:
    project = arguments.get("project", arguments.get("project_id"))
    if not isinstance(project, str) or not project.strip():
        raise ProposalError("A durable write requires an explicit project.")
    project = project.strip()
    arguments = write_arguments(arguments)
    listing = call_native("bm_project", {"command": "list"})
    projects = listing.get("projects", [])
    names = [(entry.get("qualified_name") or entry["name"], entry) for entry in projects]
    selector = parse_project(project)
    if isinstance(selector, ProjectById):
        matches = [(name, entry) for name, entry in names if entry["external_id"] == selector.external_id]
    else:
        matches = [(name, entry) for name, entry in names if project in (name, entry["name"])]
        if not matches:
            token = generate_permalink(project)
            matches = [
                (name, entry)
                for name, entry in names
                if token in (generate_permalink(name), generate_permalink(entry["name"]))
            ]
    if len(matches) != 1 or (listing.get("constrained_project") and len(projects) != 1):
        raise ProposalError(f"Cannot unambiguously resolve durable-write project {project!r} in this session.")
    project_name, selected = matches[0]
    project_id = str(UUID(selected["external_id"]))
    arguments.pop("project_id", None)
    arguments["project"] = project_id

    identifier = arguments.get("identifier", arguments.get("file_path"))
    if identifier is not None:
        if not isinstance(identifier, str):
            raise ProposalError("A durable-write identifier must be a file path.")
        path = memory_url_path(identifier).lstrip("/")
        if not isinstance(selector, ProjectById):
            prefixes = {generate_permalink(spelling) for name, entry in names for spelling in (name, entry["name"])}
            route = split_project_permalink_prefix(path, prefixes)
            if route is not None:
                prefix, path = route
                owners = {
                    entry["external_id"]
                    for name, entry in names
                    if prefix in (generate_permalink(name), generate_permalink(entry["name"]))
                }
                if owners != {project_id}:
                    raise ProposalError("The durable-write file path names a different or ambiguous project.")
        target = PurePosixPath(path)
        if not target.name or path.endswith("/"):
            raise ProposalError("A durable-write identifier must name a note file.")
        if not target.suffix:
            target = target.with_name(target.name + ".md")
        elif target.suffix.lower() not in RUNTIME_MARKDOWN_FILE_SUFFIXES:
            raise ProposalError("A durable-write identifier must name a Markdown file.")
        arguments.pop("file_path", None)
        arguments["identifier"] = target.as_posix()
    return project_name, arguments


def temporary_arguments(arguments: dict[str, Any], call_native: NativeCall) -> dict[str, Any] | None:
    fields = effective_metadata(arguments)
    status = fields.get("status")
    if fields.get("kind") != "temporary" or status not in ("active", "completed", "archived"):
        return None
    if status == "active" and not valid_last_activity(fields.get("last_activity")):
        return None

    project = arguments.get("project", arguments.get("project_id"))
    identifier = arguments.get("identifier", arguments.get("file_path"))
    directory = arguments.get("directory", arguments.get("folder", arguments.get("dir")))
    value = identifier if identifier is not None else directory
    if not isinstance(project, str) or not project.strip() or not isinstance(value, str):
        return None
    if identifier is not None and (directory is not None or value.endswith("/")):
        return None
    path = value.removeprefix("memory://").lstrip("/") if identifier is not None else value.strip("/")
    if value.startswith("/") or any(character in path for character in ("\\", ":", "\x00")):
        return None
    if not valid_project_path_value(path) or not path:
        return None
    parts = PurePosixPath(path).parts
    if not parts or not {"temporary", "handovers"}.intersection(parts):
        return None

    projects = call_native("bm_project", {"command": "list"}).get("projects", [])
    project = project.strip()
    matches = [entry for entry in projects if project in (entry.get("name"), entry.get("external_id"))]
    if len(matches) != 1 or matches[0].get("source") != "local":
        return None
    selected = matches[0]
    project_id = str(UUID(selected["external_id"]))
    if identifier is not None and project != project_id:
        selected_prefix = generate_permalink(selected["name"])
        route = split_project_permalink_prefix(path, (generate_permalink(entry["name"]) for entry in projects))
        if route is not None:
            prefix, path = route
            if prefix != selected_prefix:
                return None

    target = PurePosixPath(path)
    if not target.parts or target.parts[0] not in {"temporary", "handovers"}:
        return None
    if identifier is not None:
        if len(target.parts) < 2 or (target.suffix and target.suffix.lower() not in {".md", ".markdown"}):
            return None
        if not target.suffix:
            target = target.with_suffix(".md")

    root = Path(selected["local_path"]).expanduser().resolve()
    try:
        resolved = resolve_path_within_root(target.as_posix(), root)
    except ValueError:
        return None
    if not resolved.is_relative_to(root / target.parts[0]):
        return None

    forwarded = write_arguments(arguments)
    for key in ("project_id", "file_path", "folder", "dir", "identifier", "directory"):
        forwarded.pop(key, None)
    forwarded["project"] = project_id
    forwarded["identifier" if identifier is not None else "directory"] = target.as_posix()

    checksum = forwarded.get("expected_checksum")
    if checksum is None:
        return forwarded if status == "active" else None
    if identifier is None:
        return None
    existing = call_native("bm_read", {"identifier": target.as_posix(), "project": project_id})
    if existing.get("file_path") != target.as_posix() or not isinstance(existing.get("frontmatter"), dict):
        return None
    if existing["frontmatter"].get("kind") != "temporary":
        return None
    if existing.get("checksum") != checksum:
        raise ProposalError("Revision conflict: the temporary note changed since it was read.")
    return forwarded
