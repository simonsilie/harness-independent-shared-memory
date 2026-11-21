"""Owner CLI for listing, approving and rejecting durable-write proposals."""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import configargparse
from loguru import logger

from .proposals import (
    Config,
    ProposalError,
    audit,
    expired,
    list_proposals,
    load_config,
    load_proposal,
    proposal_lock,
    save_proposal,
    utc_now,
    warn,
    write_arguments,
)


def native_write(config: Config, arguments: dict[str, Any]) -> None:
    """Perform the approved write through one short-lived native MCP session."""
    environment = os.environ | (config.env or {})
    process = subprocess.Popen(
        config.native_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=environment,
    )
    assert process.stdin is not None and process.stdout is not None

    def call(message: dict[str, Any], expected_id: int) -> dict[str, Any]:
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        while True:
            line = process.stdout.readline()
            if not line:
                raise ProposalError("Native MCP server closed before replying")
            reply = json.loads(line)
            if reply.get("id") != expected_id:
                continue
            if "error" in reply:
                raise ProposalError(f"Native MCP error: {reply['error']}")
            result = reply.get("result")
            if not isinstance(result, dict):
                raise ProposalError("Native MCP reply had no result object")
            return result

    try:
        call(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "shared-memory-approval", "version": "1.0"},
                },
            },
            1,
        )
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        result = call(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "bm_write", "arguments": arguments},
            },
            2,
        )
        blocks = result.get("content") or []
        if not isinstance(blocks, list):
            raise ProposalError(f"Unexpected native content: {blocks!r}")
        text = "\n".join(
            block.get("text", "") for block in blocks if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
        if result.get("isError"):
            raise ProposalError(f"Native write refused: {text}")
    finally:
        try:
            process.stdin.close()
        except OSError as error:
            warn(f"Could not close native stdin: {error}")
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                warn("Native MCP server did not stop after terminate; killing it")
                process.kill()
                process.wait()


def show(proposal: dict[str, Any], arguments: dict[str, Any]) -> None:
    content = arguments["content"]
    visible_content = "".join(
        character if character.isprintable() or character in "\n\t" else ascii(character)[1:-1] for character in content
    )
    options = {key: value for key, value in arguments.items() if key != "content"}
    sys.stdout.write(
        f"Proposal: {proposal['id']}\n"
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


def require_pending(proposal: dict[str, Any]) -> None:
    if proposal.get("status") != "pending":
        raise ProposalError(f"Proposal is already {proposal['status']}")
    if expired(proposal):
        raise ProposalError("Proposal has expired")


def command_approve(config: Config, proposal_id: str, confirm: Callable[[str], bool] | None = None) -> int:
    proposal = load_proposal(config, proposal_id)
    require_pending(proposal)
    arguments = write_arguments(proposal["arguments"])
    show(proposal, arguments)
    decide = confirm or confirm_in_terminal
    if not decide("Approve this exact write? [y/N] "):
        audit(config, "approval_declined", proposal_id=proposal_id, project=proposal["project"])
        logger.info("Not approved; nothing was written.")
        return 1
    with proposal_lock(config):
        current = load_proposal(config, proposal_id)
        require_pending(current)
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
    logger.info("Approved and written: {}", proposal_id)
    return 0


def command_reject(config: Config, proposal_id: str) -> int:
    with proposal_lock(config):
        proposal = load_proposal(config, proposal_id)
        if proposal.get("status") != "pending":
            raise ProposalError(f"Proposal is already {proposal['status']}")
        proposal["status"] = "rejected"
        save_proposal(config, proposal)
        audit(config, "proposal_rejected", proposal_id=proposal_id, project=proposal["project"])
    logger.info("Rejected: {}", proposal_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = configargparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json"), env_var="SHARED_MEMORY_APPROVAL_CONFIG"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    approve = commands.add_parser("approve")
    approve.add_argument("proposal_id")
    reject = commands.add_parser("reject")
    reject.add_argument("proposal_id")
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
