"""Proposal store, classification and audit log for the durable-write gate."""

import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Iterator

from basic_memory.file_utils import ParseError, has_frontmatter, parse_frontmatter
from basic_memory.utils import coerce_dict
from loguru import logger
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, field_validator


class ProposalError(ValueError):
    """An invalid or unusable approval proposal."""


def _expanduser(value: Any) -> Any:
    return Path(value).expanduser() if isinstance(value, (str, Path)) else value


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    native_command: list[str] = Field(min_length=1)
    proposals_dir: Annotated[Path, BeforeValidator(_expanduser)]
    audit_log: Annotated[Path, BeforeValidator(_expanduser)]
    ttl_hours: int = Field(default=24, gt=0)
    env: dict[str, str] | None = None

    @field_validator("native_command")
    @classmethod
    def expand_native_executable(cls, command: list[str]) -> list[str]:
        if command[0].startswith("~"):
            return [str(Path(command[0]).expanduser()), *command[1:]]
        return command


def warn(message: str) -> None:
    logger.warning("approval gate: {}", message)


def load_config(path: Path) -> Config:
    try:
        return Config.model_validate(json.loads(path.read_text()))
    except ValidationError as error:
        raise ProposalError(f"Invalid config {path}: {error}") from error


def prepare(config: Config) -> None:
    config.proposals_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    config.proposals_dir.chmod(0o700)
    config.audit_log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    config.audit_log.parent.chmod(0o700)
    if config.audit_log.exists():
        config.audit_log.chmod(0o600)


def audit(config: Config, event: str, **fields: Any) -> None:
    record = {"timestamp": utc_now(), "event": event, **fields}
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    old_umask = os.umask(0o077)
    try:
        with config.audit_log.open("ab") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(payload)
            stream.flush()
    finally:
        os.umask(old_umask)


@contextmanager
def proposal_lock(config: Config) -> Iterator[None]:
    prepare(config)
    with (config.proposals_dir / ".lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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


def _proposal_path(config: Config, proposal_id: str) -> Path:
    if not proposal_id or "/" in proposal_id or "\\" in proposal_id or proposal_id in {".", ".."}:
        raise ProposalError(f"Unsafe proposal id: {proposal_id!r}")
    return config.proposals_dir / f"{proposal_id}.json"


def save_proposal(config: Config, proposal: dict[str, Any]) -> None:
    path = _proposal_path(config, proposal["id"])
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=config.proposals_dir)
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump(proposal, stream, indent=2, sort_keys=True)
            stream.write("\n")
        Path(temporary).chmod(0o600)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def load_proposal(config: Config, proposal_id: str) -> dict[str, Any]:
    path = _proposal_path(config, proposal_id)
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ProposalError(f"Unknown proposal: {proposal_id}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ProposalError(f"Unreadable proposal {proposal_id}: {error}") from error


def list_proposals(config: Config) -> list[dict[str, Any]]:
    proposals = []
    for path in sorted(config.proposals_dir.glob("*.json")):
        proposals.append(load_proposal(config, path.stem))
    return proposals


def expired(proposal: dict[str, Any]) -> bool:
    try:
        deadline = datetime.fromisoformat(proposal["expires_at"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, ValueError) as error:
        raise ProposalError(f"Proposal {proposal.get('id')} has an invalid expiry: {error}") from error
    return datetime.now(timezone.utc) >= deadline


def create_or_reuse(config: Config, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Bind a durable write to a proposal, reusing an identical open one."""
    project = arguments.get("project", arguments.get("project_id"))
    if not isinstance(project, str) or not project.strip():
        raise ProposalError("A durable write requires an explicit project.")
    content = arguments.get("content")
    if not isinstance(content, str):
        raise ProposalError("A durable write requires string content.")
    arguments = write_arguments(arguments)
    payload = json.dumps(arguments, sort_keys=True)
    digest = content_hash(content)
    source = effective_metadata(arguments).get("source")
    with proposal_lock(config):
        for proposal in list_proposals(config):
            if (
                proposal.get("status") == "pending"
                and not expired(proposal)
                and json.dumps(proposal.get("arguments"), sort_keys=True) == payload
            ):
                return proposal, False
        created = utc_now()
        expires = (datetime.now(timezone.utc) + timedelta(hours=config.ttl_hours)).replace(microsecond=0)
        proposal = {
            "id": uuid.uuid4().hex,
            "status": "pending",
            "created_at": created,
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "project": project,
            "content": content,
            "content_hash": digest,
            "source": None if source is None else str(source),
            "arguments": arguments,
        }
        save_proposal(config, proposal)
        audit(
            config,
            "proposal_created",
            proposal_id=proposal["id"],
            project=project,
            content_hash=digest,
            source=proposal["source"],
        )
        return proposal, True
