"""File-backed approval proposals and their audit log."""

import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from . import ProposalError
from .config import Config
from .writes import NativeCall, effective_metadata, pin_durable_target


def prepare(config: Config) -> None:
    config.proposals_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    config.proposals_dir.chmod(0o700)
    config.audit_log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if config.audit_log.exists():
        config.audit_log.chmod(0o600)


def audit(config: Config, event: str, **fields: Any) -> None:
    record = {"timestamp": utc_now(), "event": event, **fields}
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(config.audit_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "ab") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(payload)
        stream.flush()


@contextmanager
def proposal_lock(config: Config) -> Iterator[None]:
    prepare(config)
    with (config.proposals_dir / ".lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def utc_now(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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


def expired(proposal: dict[str, Any], *, now: datetime | None = None) -> bool:
    try:
        deadline = datetime.fromisoformat(proposal["expires_at"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, ValueError) as error:
        raise ProposalError(f"Proposal {proposal.get('id')} has an invalid expiry: {error}") from error
    return (now or datetime.now(timezone.utc)) >= deadline


def create_or_reuse(
    config: Config, arguments: dict[str, Any], call_native: NativeCall, *, now: datetime | None = None
) -> tuple[dict[str, Any], bool]:
    """Bind a durable write to a proposal, reusing an identical open one."""
    content = arguments.get("content")
    if not isinstance(content, str):
        raise ProposalError("A durable write requires string content.")
    project, arguments = pin_durable_target(arguments, call_native)
    payload = json.dumps(arguments, sort_keys=True)
    digest = content_hash(content)
    source = effective_metadata(arguments).get("source")
    with proposal_lock(config):
        current_time = now or datetime.now(timezone.utc)
        for proposal in list_proposals(config):
            if (
                proposal.get("status") == "pending"
                and proposal.get("project_external_id") == arguments["project"]
                and not expired(proposal, now=current_time)
                and json.dumps(proposal.get("arguments"), sort_keys=True) == payload
            ):
                return proposal, False
        expires = current_time + timedelta(hours=config.ttl_hours)
        proposal = {
            "id": uuid.uuid4().hex,
            "status": "pending",
            "created_at": utc_now(current_time),
            "expires_at": utc_now(expires),
            "project": project,
            "project_external_id": arguments["project"],
            "content": content,
            "content_hash": digest,
            "source": None if source is None else str(source),
            "arguments": arguments,
        }
        save_proposal(config, proposal)
        try:
            audit(
                config,
                "proposal_created",
                proposal_id=proposal["id"],
                project=project,
                content_hash=digest,
                source=proposal["source"],
            )
        except OSError:
            _proposal_path(config, proposal["id"]).unlink()
            raise
        return proposal, True
