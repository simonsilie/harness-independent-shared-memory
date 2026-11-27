"""Reserve and apply owner decisions on durable-write proposals."""

from collections.abc import Callable
from typing import Any

from . import ProposalError
from .config import Config
from .native import NativePreflightError, NativeWriteRefused, native_write, warn
from .proposals import (
    audit,
    expired,
    load_proposal,
    proposal_lock,
    save_proposal,
    utc_now,
)
from .writes import write_arguments


def _require_pending(proposal: dict[str, Any]) -> None:
    if proposal.get("status") != "pending":
        raise ProposalError(f"Proposal is already {proposal['status']}")
    if expired(proposal):
        raise ProposalError("Proposal has expired")


def approve(
    config: Config,
    proposal_id: str,
    confirm: Callable[[dict[str, Any], dict[str, Any]], bool],
) -> bool:
    proposal = load_proposal(config, proposal_id)
    _require_pending(proposal)
    arguments = write_arguments(proposal["arguments"])
    if not proposal.get("project_external_id") or proposal["project_external_id"] != arguments.get("project"):
        raise ProposalError("This proposal has no pinned project UUID. Submit the write again for approval.")
    if not confirm(proposal, arguments):
        audit(config, "approval_declined", proposal_id=proposal_id, project=proposal["project"])
        return False
    try:
        with proposal_lock(config):
            current = load_proposal(config, proposal_id)
            _require_pending(current)
            if current != proposal:
                raise ProposalError("Proposal changed during confirmation.")
            # Audit first so an audit I/O failure leaves an unsubmitted proposal retryable.
            audit(config, "proposal_applying", proposal_id=proposal_id, project=proposal["project"])
            # Reserve before calling the native server. A lost reply can follow a committed write.
            proposal["status"] = "applying"
            save_proposal(config, proposal)
    except OSError as error:
        raise ProposalError(f"Could not record approval for {proposal_id}: {error}") from error
    try:
        native_write(config, arguments)
    except (OSError, ValueError) as error:
        message = str(error)
        if isinstance(error, NativePreflightError):
            status, event = "pending", "proposal_preflight_failed"
        elif isinstance(error, NativeWriteRefused):
            status, event = "refused", "proposal_refused"
        else:
            status, event = "outcome_unknown", "proposal_outcome_unknown"
            message = f"Check the native store before proposing another write: {error}"
        recorded_status = "applying"
        try:
            with proposal_lock(config):
                proposal["status"] = status
                save_proposal(config, proposal)
                recorded_status = status
                audit(config, event, proposal_id=proposal_id, project=proposal["project"])
        except OSError as record_error:
            message += f" Could not finish recording the failure for proposal {proposal_id} ({recorded_status}): {record_error}"
        else:
            if isinstance(error, (NativePreflightError, NativeWriteRefused)):
                raise
        raise ProposalError(message) from error
    try:
        with proposal_lock(config):
            proposal["status"] = "approved"
            proposal["approved_at"] = utc_now()
            save_proposal(config, proposal)
            try:
                audit(
                    config,
                    "proposal_approved",
                    proposal_id=proposal_id,
                    project=proposal["project"],
                    content_hash=proposal["content_hash"],
                )
            except OSError as error:
                warn(f"Could not record the final audit event for approved proposal {proposal_id}: {error}")
    except OSError as error:
        raise ProposalError(
            f"The note was written, but proposal {proposal_id} could not be marked approved and stays applying: {error}"
        ) from error
    return True


def reject(config: Config, proposal_id: str) -> None:
    with proposal_lock(config):
        proposal = load_proposal(config, proposal_id)
        if proposal.get("status") != "pending":
            raise ProposalError(f"Proposal is already {proposal['status']}")
        proposal["status"] = "rejected"
        save_proposal(config, proposal)
        audit(config, "proposal_rejected", proposal_id=proposal_id, project=proposal["project"])
