"""Native MCP transport for approved writes."""

import json
import os
import subprocess
from typing import Any

from loguru import logger

from . import ProposalError
from .config import Config


def warn(message: str) -> None:
    logger.warning("approval gate: {}", message)


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
