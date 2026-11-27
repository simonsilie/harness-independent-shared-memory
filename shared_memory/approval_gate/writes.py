"""Write validation and eligibility for automatic temporary writes."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from . import ProposalError
from .basic_memory_api import (
    RUNTIME_MARKDOWN_FILE_SUFFIXES,
    ParseError,
    ProjectById,
    coerce_dict,
    generate_permalink,
    has_frontmatter,
    memory_url_path,
    parse_frontmatter,
    parse_project,
    resolve_path_within_root,
    split_project_permalink_prefix,
    valid_project_path_value,
)

# Client-supplied MCP tool arguments: arbitrary JSON that each function validates for the keys it uses.
type ToolArguments = dict[str, Any]
type NativeCall = Callable[[str, ToolArguments], Awaitable[dict[str, Any]]]


class ProjectEntry(TypedDict):
    """One project from the native ``bm_project`` list reply, limited to the fields used here."""

    name: str
    qualified_name: NotRequired[str | None]
    external_id: str
    source: NotRequired[str]
    local_path: NotRequired[str]


class ProjectListing(TypedDict):
    """The native ``bm_project`` list reply, limited to the fields used here."""

    projects: list[ProjectEntry]
    constrained_project: NotRequired[str | None]


class NoteRead(TypedDict, total=False):
    """The native ``bm_read`` reply, limited to the fields used here."""

    file_path: str
    frontmatter: dict[str, Any]
    checksum: str


async def list_projects(call_native: NativeCall) -> ProjectListing:
    # Missing keys surface as LookupError, which the proxy reports as an unexpected native response.
    return cast(ProjectListing, await call_native("bm_project", {"command": "list"}))


def effective_metadata(arguments: ToolArguments) -> dict[str, Any]:
    """Merge a write's frontmatter with its explicit metadata.

    Parameters
    ----------
    arguments : ToolArguments
        ``bm_write`` arguments with string ``content`` and optional ``metadata``.

    Returns
    -------
    dict[str, Any]
        Frontmatter fields, overridden by explicit metadata fields.

    Raises
    ------
    ProposalError
        If the content is not a string, its frontmatter is malformed or the metadata is not an object.
    """
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
    """Return whether ``value`` is a UTC timestamp, as a datetime or ISO 8601 string."""
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


def write_arguments(arguments: ToolArguments) -> ToolArguments:
    """Normalize the overwrite policy of a write.

    Parameters
    ----------
    arguments : ToolArguments
        ``bm_write`` arguments with optional ``expected_checksum`` and ``overwrite``.

    Returns
    -------
    ToolArguments
        A copy of the arguments. Without a checksum, ``overwrite`` is set to ``False`` so the write
        can only create a note.

    Raises
    ------
    ProposalError
        If the write would replace a note without a usable checksum, or ``overwrite`` is not a boolean.
    """
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


def _display_name(entry: ProjectEntry) -> str:
    return entry.get("qualified_name") or entry["name"]


def _permalinks(entry: ProjectEntry) -> set[str]:
    return {generate_permalink(_display_name(entry)), generate_permalink(entry["name"])}


def resolve_project(project: str, listing: ProjectListing) -> tuple[ProjectEntry, bool]:
    """Resolve a project selector to exactly one listed project.

    Parameters
    ----------
    project : str
        A project UUID, name, qualified name or permalink.
    listing : ProjectListing
        The native project list of the session that will execute the write.

    Returns
    -------
    tuple[ProjectEntry, bool]
        The matching project, and whether the selector was a UUID.

    Raises
    ------
    ProposalError
        If no project or more than one project matches, or the session is constrained to a
        different set of projects.
    """
    projects = listing.get("projects", [])
    selector = parse_project(project)
    by_id = isinstance(selector, ProjectById)
    if by_id:
        matches = [entry for entry in projects if entry["external_id"] == selector.external_id]
    else:
        matches = [entry for entry in projects if project in (_display_name(entry), entry["name"])]
        if not matches:
            token = generate_permalink(project)
            matches = [entry for entry in projects if token in _permalinks(entry)]
    if len(matches) != 1 or (listing.get("constrained_project") and len(projects) != 1):
        raise ProposalError(f"Cannot unambiguously resolve project {project!r} in this session.")
    return matches[0], by_id


def strip_project_prefix(path: str, listing: ProjectListing, project_id: str) -> str:
    """Drop a leading project permalink from a note path.

    Parameters
    ----------
    path : str
        A note path that may start with a project permalink.
    listing : ProjectListing
        The native project list used to recognize permalinks.
    project_id : str
        The UUID of the project the write targets.

    Returns
    -------
    str
        The path without the permalink, or unchanged if it has none.

    Raises
    ------
    ProposalError
        If the permalink names a different project or more than one project.
    """
    projects = listing.get("projects", [])
    route = split_project_permalink_prefix(path, set().union(*map(_permalinks, projects)))
    if route is None:
        return path
    prefix, path = route
    if {entry["external_id"] for entry in projects if prefix in _permalinks(entry)} != {project_id}:
        raise ProposalError("The file path names a different or ambiguous project.")
    return path


def pin_durable_target(arguments: ToolArguments, listing: ProjectListing) -> tuple[str, ToolArguments]:
    """Pin a durable write to one project UUID and one Markdown note path.

    Parameters
    ----------
    arguments : ToolArguments
        Client ``bm_write`` arguments.
    listing : ProjectListing
        The native project list of the session that will execute the write.

    Returns
    -------
    tuple[str, ToolArguments]
        The project's display name, and the arguments with ``project`` set to its UUID and any note
        path normalized into ``identifier``.

    Raises
    ------
    ProposalError
        If the project is missing or ambiguous, the overwrite policy is invalid, or the identifier
        does not name a Markdown file.
    """
    project = arguments.get("project", arguments.get("project_id"))
    if not isinstance(project, str) or not project.strip():
        raise ProposalError("A durable write requires an explicit project.")
    project = project.strip()
    arguments = write_arguments(arguments)
    selected, by_id = resolve_project(project, listing)
    project_id = str(UUID(selected["external_id"]))
    arguments.pop("project_id", None)
    arguments["project"] = project_id

    identifier = arguments.get("identifier", arguments.get("file_path"))
    if identifier is not None:
        if not isinstance(identifier, str):
            raise ProposalError("A durable-write identifier must be a file path.")
        path = memory_url_path(identifier).lstrip("/")
        if not by_id:
            path = strip_project_prefix(path, listing, project_id)
        target = PurePosixPath(path)
        if not target.name or path.endswith("/"):
            raise ProposalError("A durable-write identifier must name a note file.")
        if not target.suffix:
            target = target.with_name(target.name + ".md")
        elif target.suffix.lower() not in RUNTIME_MARKDOWN_FILE_SUFFIXES:
            raise ProposalError("A durable-write identifier must name a Markdown file.")
        arguments.pop("file_path", None)
        arguments["identifier"] = target.as_posix()
    return _display_name(selected), arguments


async def temporary_arguments(
    arguments: ToolArguments, listing: ProjectListing, call_native: NativeCall
) -> ToolArguments | None:
    """Return the forwarded arguments of a write that may bypass approval as temporary.

    Parameters
    ----------
    arguments : ToolArguments
        Client ``bm_write`` arguments.
    listing : ProjectListing
        The native project list of the session that will execute the write.
    call_native : NativeCall
        Calls a tool on the native session that will execute the write.

    Returns
    -------
    ToolArguments or None
        The arguments pinned to the project UUID and a path under ``temporary/`` or ``handovers/``
        of a local project, or ``None`` if the write is not clearly temporary and needs approval.

    Raises
    ------
    ProposalError
        If the content, metadata or overwrite policy is invalid, or a checksum-guarded update of a
        temporary note no longer matches the native checksum.
    """
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
    path = memory_url_path(value).lstrip("/") if identifier is not None else value.strip("/")
    if any(character in path for character in ("\\", ":", "\x00")):
        return None
    if not valid_project_path_value(path) or not path:
        return None
    parts = PurePosixPath(path).parts
    if not parts or not {"temporary", "handovers"}.intersection(parts):
        return None

    try:
        selected, by_id = resolve_project(project.strip(), listing)
        project_id = str(UUID(selected["external_id"]))
        if identifier is not None and not by_id:
            path = strip_project_prefix(path, listing, project_id)
    except ProposalError:
        # Anything not clearly temporary falls through to the durable proposal path.
        return None
    if selected.get("source") != "local":
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
    existing = cast(NoteRead, await call_native("bm_read", {"identifier": target.as_posix(), "project": project_id}))
    if existing.get("file_path") != target.as_posix() or not isinstance(existing.get("frontmatter"), dict):
        return None
    if existing["frontmatter"].get("kind") != "temporary":
        return None
    if existing.get("checksum") != checksum:
        raise ProposalError("Revision conflict: the temporary note changed since it was read.")
    return forwarded
