"""Reserve and apply owner decisions on durable-write proposals."""

from collections.abc import Callable
from typing import Any

from . import ProposalError
from .config import Config
from .native import native_write
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
    if not confirm(proposal, arguments):
        audit(config, "approval_declined", proposal_id=proposal_id, project=proposal["project"])
        return False
    with proposal_lock(config):
        current = load_proposal(config, proposal_id)
        _require_pending(current)
        if current != proposal:
            raise ProposalError("Proposal changed during confirmation.")
        # Reserve before calling the native server. A lost reply can follow a committed write.
        proposal["status"] = "applying"
        save_proposal(config, proposal)
        audit(config, "proposal_applying", proposal_id=proposal_id, project=proposal["project"])
    try:
        native_write(config, arguments)
    except (OSError, ValueError) as error:
        proposal["status"] = "outcome_unknown"
        save_proposal(config, proposal)
        audit(config, "proposal_outcome_unknown", proposal_id=proposal_id, project=proposal["project"])
        raise ProposalError(f"Check the native store before proposing another write: {error}") from error
    proposal["status"] = "approved"
    proposal["approved_at"] = utc_now()
    save_proposal(config, proposal)
    audit(
        config,
        "proposal_approved",
        proposal_id=proposal_id,
        project=proposal["project"],
        content_hash=proposal["content_hash"],
    )
    return True


def reject(config: Config, proposal_id: str) -> None:
    with proposal_lock(config):
        proposal = load_proposal(config, proposal_id)
        if proposal.get("status") != "pending":
            raise ProposalError(f"Proposal is already {proposal['status']}")
        proposal["status"] = "rejected"
        save_proposal(config, proposal)
        audit(config, "proposal_rejected", proposal_id=proposal_id, project=proposal["project"])
