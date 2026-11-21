"""Owner CLI for listing, approving and rejecting durable-write proposals."""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import configargparse
from loguru import logger

from . import ProposalError
from .approvals import approve, reject
from .config import Config, load_config
from .proposals import expired, list_proposals


def show(proposal: dict[str, Any], arguments: dict[str, Any]) -> None:
    content = arguments["content"]
    visible_content = "".join(
        character if character.isprintable() or character in "\n\t" else ascii(character)[1:-1] for character in content
    )
    options = {key: value for key, value in arguments.items() if key != "content"}
    sys.stdout.write(
        f"Proposal: {proposal['id']}\n"
        f"Project:  {json.dumps(proposal['project'])}\n"
        f"Source:   {json.dumps(proposal.get('source'))}\n"
        f"Expires:  {proposal['expires_at']}\n"
        f"Hash:     {proposal['content_hash']}\n"
        f"Write arguments: {json.dumps(options, indent=2, sort_keys=True)}\n"
        f"--- content ---\n{visible_content}\n--- end ---\n"
    )
    sys.stdout.flush()


def confirm_in_terminal(prompt: str) -> bool:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise ProposalError("Approval requires an interactive terminal for input and output.")
    return input(prompt).strip().lower() in {"y", "yes"}


def command_list(config: Config) -> int:
    proposals = [p for p in list_proposals(config) if p.get("status") in {"pending", "applying", "outcome_unknown"}]
    if not proposals:
        sys.stdout.write("No pending proposals.\n")
        return 0
    for proposal in sorted(proposals, key=lambda p: p["created_at"]):
        state = proposal["status"]
        if state == "pending" and expired(proposal):
            state = "EXPIRED"
        sys.stdout.write(f"{proposal['id']}  {proposal['project']}  {state}  expires {proposal['expires_at']}\n")
    return 0


def command_approve(config: Config, proposal_id: str, confirm: Callable[[str], bool] | None = None) -> int:
    decide = confirm or confirm_in_terminal

    def review(proposal: dict[str, Any], arguments: dict[str, Any]) -> bool:
        show(proposal, arguments)
        return decide("Approve this exact write? [y/N] ")

    if not approve(config, proposal_id, review):
        logger.info("Not approved; nothing was written.")
        return 1
    logger.info("Approved and written: {}", proposal_id)
    return 0


def command_reject(config: Config, proposal_id: str) -> int:
    reject(config, proposal_id)
    logger.info("Rejected: {}", proposal_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = configargparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json"), env_var="SHARED_MEMORY_APPROVAL_CONFIG"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    approve_parser = commands.add_parser("approve")
    approve_parser.add_argument("proposal_id")
    reject_parser = commands.add_parser("reject")
    reject_parser.add_argument("proposal_id")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    try:
        if args.command == "list":
            return command_list(config)
        if args.command == "approve":
            return command_approve(config, args.proposal_id)
        return command_reject(config, args.proposal_id)
    except ProposalError as error:
        logger.error("{}", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
