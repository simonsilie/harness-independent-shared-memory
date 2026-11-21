"""Native MCP transport for approved writes."""

import asyncio
import json
import os
from contextlib import suppress
from typing import Any

from loguru import logger

from . import ProposalError
from .config import Config

REQUEST_TIMEOUT = 20
SHUTDOWN_TIMEOUT = 10


class NativePreflightError(ProposalError):
    """The native session failed before a write was submitted."""


def warn(message: str) -> None:
    logger.warning("approval gate: {}", message)


async def _shutdown(process: asyncio.subprocess.Process) -> None:
    assert process.stdin is not None
    process.stdin.close()
    # Basic Memory drains accepted writes to Markdown during its EOF shutdown.
    shutdown = asyncio.create_task(process.communicate())
    try:
        await asyncio.wait_for(asyncio.shield(shutdown), SHUTDOWN_TIMEOUT)
    except TimeoutError as error:
        with suppress(ProcessLookupError):
            process.terminate()
        try:
            await asyncio.wait_for(asyncio.shield(shutdown), SHUTDOWN_TIMEOUT)
        except TimeoutError:
            with suppress(ProcessLookupError):
                process.kill()
            with suppress(TimeoutError):
                await asyncio.wait_for(shutdown, SHUTDOWN_TIMEOUT)
        raise ProposalError("Native MCP server timed out during graceful shutdown.") from error
    if process.returncode != 0:
        raise ProposalError(f"Native MCP server exited with status {process.returncode}.")


async def _native_write(config: Config, arguments: dict[str, Any]) -> None:
    try:
        process = await asyncio.create_subprocess_exec(
            *config.native_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,
            env=os.environ | (config.env or {}),
        )
    except OSError as error:
        raise NativePreflightError(f"Could not start native MCP server: {error}") from error
    assert process.stdin is not None and process.stdout is not None

    async def send(message: dict[str, Any]) -> None:
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

    async def call(method: str, params: dict[str, Any], request_id: int, label: str) -> dict[str, Any]:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                await send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
                while line := await process.stdout.readline():
                    reply = json.loads(line)
                    if not isinstance(reply, dict):
                        raise ProposalError(f"Native {label} response was not a JSON object.")
                    if reply.get("id") != request_id:
                        continue
                    if "error" in reply:
                        raise ProposalError(f"Native {label} error: {reply['error']}")
                    result = reply.get("result")
                    if not isinstance(result, dict):
                        raise ProposalError(f"Native {label} reply had no result object.")
                    if result.get("isError"):
                        raise ProposalError(f"Native {label} refused: {result.get('content')}")
                    return result
                raise ProposalError(f"Native MCP server closed before replying to {label}.")
        except TimeoutError as error:
            raise ProposalError(f"Native {label} timed out.") from error

    write_submitted = False
    write_acknowledged = False
    try:
        await call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "shared-memory-approval", "version": "1.0"},
            },
            1,
            "initialize",
        )
        async with asyncio.timeout(REQUEST_TIMEOUT):
            await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        result = await call(
            "tools/call",
            {"name": "bm_project", "arguments": {"command": "list", "output_format": "json"}},
            2,
            "bm_project",
        )
        listing = result.get("structuredContent")
        if not isinstance(listing, dict):
            raise ProposalError("Native bm_project did not return structured data.")
        listing = listing.get("result", listing)
        projects = listing.get("projects") if isinstance(listing, dict) else None
        if not isinstance(projects, list) or not all(isinstance(project, dict) for project in projects):
            raise ProposalError("Native bm_project did not return a project list.")
        matches = [project for project in projects if project.get("external_id") == arguments["project"]]
        if len(matches) != 1 or (listing.get("constrained_project") and len(projects) != 1):
            raise ProposalError("The native session cannot unambiguously address the approved project UUID.")

        write_submitted = True
        await call("tools/call", {"name": "bm_write", "arguments": arguments}, 3, "bm_write")
        write_acknowledged = True
    except (OSError, ValueError) as error:
        if not write_submitted:
            raise NativePreflightError(f"Native write was not submitted: {error}") from error
        raise
    finally:
        try:
            await _shutdown(process)
        except (OSError, ProposalError) as error:
            if write_acknowledged:
                raise
            warn(f"Could not shut down native MCP server: {error}")


def native_write(config: Config, arguments: dict[str, Any]) -> None:
    asyncio.run(_native_write(config, arguments))
