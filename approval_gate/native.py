"""Native MCP transport shared by the proxy and approved writes."""

import asyncio
import hashlib
import json
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger

from . import ProposalError
from .basic_memory_api import resolve_path_within_root
from .config import Config

REQUEST_TIMEOUT = 20
SHUTDOWN_TIMEOUT = 10
MESSAGE_LIMIT = 16 * 1024 * 1024
PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
# MCP 2026-07-28 clients skip initialize and send these keys with every request.
ENVELOPE_KEYS = (
    PROTOCOL_VERSION_KEY,
    "io.modelcontextprotocol/clientCapabilities",
    "io.modelcontextprotocol/clientInfo",
)
# Approved writes use the revision of the real clients, so the native server sees one protocol era from the gate.
APPROVAL_ENVELOPE = {
    PROTOCOL_VERSION_KEY: "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "shared-memory-approval", "version": "1.0"},
}
DEFINITE_REFUSALS = {
    "ALREADY_EXISTS",
    "AMBIGUOUS",
    "INVALID_ARGUMENTS",
    "LOCKED",
    "NOT_FOUND",
    "OUTSIDE_PROJECT",
    "REVISION_CONFLICT",
    "UNSUPPORTED",
}


class NativePreflightError(ProposalError):
    """The native session failed before a write was submitted."""


class NativeWriteRefused(ProposalError):
    """The native server confirmed that it did not apply the write."""


def warn(message: str) -> None:
    logger.warning("approval gate: {}", message)


def reply_result(reply: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the result object of a native JSON-RPC reply.

    Raises `NativeWriteRefused` when a `bm_write` refusal is definite, so the
    caller knows the note was not written, and `ProposalError` otherwise.
    """
    if "error" in reply:
        raise ProposalError(f"Native {name} error: {reply['error']}")
    result = reply.get("result")
    if not isinstance(result, dict):
        raise ProposalError(f"Native {name} reply had no result object.")
    if not result.get("isError"):
        return result
    content = result.get("content")
    match name, content:
        case "bm_write", [{"type": "text", "text": str(body)}]:
            with suppress(json.JSONDecodeError):
                match json.loads(body):
                    case {"error": str(code), "message": str(detail)} as refusal if code in DEFINITE_REFUSALS:
                        message = f"Native bm_write refused ({code}): {detail}"
                        suggestion = refusal.get("try_instead")
                        if isinstance(suggestion, str) and suggestion:
                            message += f" Try instead: {suggestion}"
                        raise NativeWriteRefused(message)
    raise ProposalError(f"Native {name} error: {content}")


def structured_data(result: dict[str, Any], name: str) -> dict[str, Any]:
    data = result.get("structuredContent")
    if not isinstance(data, dict):
        raise ProposalError(f"Native {name} did not return structured data.")
    data = data.get("result", data)
    if not isinstance(data, dict):
        raise ProposalError(f"Native {name} did not return an object.")
    return data


async def start_native(config: Config) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *config.native_command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        limit=MESSAGE_LIMIT,
        env=os.environ | (config.env or {}),
    )


type Forward = Callable[[bytes, Any], Awaitable[None]]


class NativeClient:
    """Send the gate's own tool calls over a native server's stdio and route their replies.

    `relay` must run while calls are pending: it is the only reader of the
    native output and hands every other message to `forward`.
    """

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        assert process.stdin is not None and process.stdout is not None
        self.stdin = process.stdin
        self._stdout = process.stdout
        # Internal ids cannot collide with client ids, so their replies are never forwarded.
        self._prefix = f"approval-gate-{uuid4().hex}-"
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._failure: ProposalError | None = None

    async def send(self, message: dict[str, Any]) -> None:
        self.stdin.write((json.dumps(message) + "\n").encode())
        await self.stdin.drain()

    async def call_tool(self, name: str, arguments: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        if self._failure is not None:
            raise self._failure
        request_id = f"{self._prefix}{uuid4().hex}"
        reply = asyncio.get_running_loop().create_future()
        self._pending[request_id] = reply
        params = {
            "name": name,
            "arguments": {**arguments, "output_format": "json"},
            **({"_meta": meta} if meta else {}),
        }
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                await self.send({"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": params})
                return reply_result(await reply, name)
        except TimeoutError as error:
            raise ProposalError(f"Native {name} timed out.") from error
        finally:
            self._pending.pop(request_id, None)

    async def relay(self, forward: Forward | None = None) -> None:
        failure = ProposalError("Native MCP server closed before replying.")
        try:
            while line := await self._stdout.readline():
                try:
                    reply = json.loads(line)
                except json.JSONDecodeError:
                    reply = None
                if isinstance(reply, dict) and "method" not in reply:
                    request_id = reply.get("id")
                    if isinstance(request_id, str) and request_id.startswith(self._prefix):
                        pending = self._pending.get(request_id)
                        if pending is not None and not pending.done():
                            pending.set_result(reply)
                        continue
                if forward is not None:
                    await forward(line, reply)
        except (OSError, ValueError) as error:
            failure = ProposalError(f"Could not read the native MCP server: {error}")
            raise
        finally:
            self._failure = failure
            for pending in self._pending.values():
                if not pending.done():
                    pending.set_exception(failure)


async def _shutdown(process: asyncio.subprocess.Process) -> None:
    assert process.stdin is not None
    process.stdin.close()
    # Basic Memory drains accepted writes to Markdown during its EOF shutdown.
    try:
        await asyncio.wait_for(process.wait(), SHUTDOWN_TIMEOUT)
    except TimeoutError as error:
        with suppress(ProcessLookupError):
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), SHUTDOWN_TIMEOUT)
        except TimeoutError:
            with suppress(ProcessLookupError):
                process.kill()
            with suppress(TimeoutError):
                await asyncio.wait_for(process.wait(), SHUTDOWN_TIMEOUT)
        raise ProposalError("Native MCP server timed out during graceful shutdown.") from error
    if process.returncode != 0:
        raise ProposalError(f"Native MCP server exited with status {process.returncode}.")


async def _native_write(config: Config, arguments: dict[str, Any]) -> None:
    try:
        process = await start_native(config)
    except OSError as error:
        raise NativePreflightError(f"Could not start native MCP server: {error}") from error
    client = NativeClient(process)
    relay = asyncio.create_task(client.relay())

    write_submitted = False
    write_acknowledged = False
    try:
        result = await client.call_tool("bm_project", {"command": "list"}, APPROVAL_ENVELOPE)
        listing = structured_data(result, "bm_project")
        projects = listing.get("projects")
        if not isinstance(projects, list) or not all(isinstance(project, dict) for project in projects):
            raise ProposalError("Native bm_project did not return a project list.")
        matches = [project for project in projects if project.get("external_id") == arguments["project"]]
        if len(matches) != 1 or (listing.get("constrained_project") and len(projects) != 1):
            raise ProposalError("The native session cannot unambiguously address the approved project UUID.")
        local_path = matches[0].get("local_path") if matches[0].get("source") == "local" else None
        if matches[0].get("source") == "local" and (not isinstance(local_path, str) or not local_path):
            raise ProposalError("The native session did not return the approved local project's path.")

        write_submitted = True
        result = await client.call_tool("bm_write", arguments, APPROVAL_ENVELOPE)
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
        finally:
            # A surviving grandchild could hold stdout open after the server exits.
            relay.cancel()
            with suppress(asyncio.CancelledError, OSError, ValueError):
                await relay

    if local_path is not None:
        change = structured_data(result, "bm_write")
        path = change.get("file_path")
        checksum = change.get("checksum")
        if not isinstance(path, str) or not path or not isinstance(checksum, str) or not checksum:
            raise ProposalError("Native bm_write did not return a path and checksum for the accepted revision.")
        try:
            markdown = resolve_path_within_root(path, Path(local_path), allow_root=False)
            with markdown.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except (OSError, ValueError) as error:
            raise ProposalError(f"Could not verify the accepted Markdown revision at {path!r}: {error}") from error
        if actual != checksum:
            raise ProposalError(f"Markdown at {path!r} does not match the accepted revision.")


def native_write(config: Config, arguments: dict[str, Any]) -> None:
    asyncio.run(_native_write(config, arguments))
