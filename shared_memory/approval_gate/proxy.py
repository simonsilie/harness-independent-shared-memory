"""Transparent stdio MCP proxy that gates durable bm_write calls."""

import asyncio
import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import configargparse

from . import ALLOWED_TOOLS, ProposalError
from .config import Config, add_config_argument, load_config
from .native import (
    ENVELOPE_KEYS,
    MESSAGE_LIMIT,
    PROTOCOL_VERSION_KEY,
    NativeClient,
    start_native,
    structured_data,
    warn,
)
from .proposals import audit, create_or_reuse, prepare
from .writes import NativeCall, list_projects, temporary_arguments


def envelope(request: dict[str, Any]) -> dict[str, Any]:
    params = request.get("params")
    meta = params.get("_meta") if isinstance(params, dict) else None
    if not isinstance(meta, dict):
        return {}
    return {key: meta[key] for key in ENVELOPE_KEYS if key in meta}


def tool_response(
    request: dict[str, Any], text: str, is_error: bool = False, proposal_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if proposal_id is not None:
        result["structuredContent"] = {"result": {"proposal_id": proposal_id, "message": text}}
    if PROTOCOL_VERSION_KEY in envelope(request):
        result["resultType"] = "complete"
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": result,
    }


@dataclass(frozen=True)
class ClientReply:
    """A response the gate sends back to the client itself."""

    message: dict[str, Any]


@dataclass(frozen=True)
class NativeRequest:
    """A rewritten request the gate forwards to the native server."""

    message: dict[str, Any]


async def handle_write(
    request: dict[str, Any], config: Config, config_path: Path, call_native: NativeCall
) -> ClientReply | NativeRequest:
    arguments = request["params"].get("arguments", {})
    if not isinstance(arguments, dict):
        return ClientReply(tool_response(request, "bm_write arguments must be an object", is_error=True))
    try:
        listing = await list_projects(call_native)
        temporary = await temporary_arguments(arguments, listing, call_native)
        if temporary is not None:
            return NativeRequest({**request, "params": {**request["params"], "arguments": temporary}})
        proposal, created = create_or_reuse(config, arguments, listing)
    except (ProposalError, LookupError, ValueError) as error:
        # A malformed native reply must not escape and stop the client relay thread.
        reason = str(error) if isinstance(error, ProposalError) else f"Unexpected native response: {error!r}"
        audit(config, "write_refused", reason=reason, id=request.get("id"))
        return ClientReply(tool_response(request, reason, is_error=True))
    if request.get("id") is None:
        audit(config, "unidentified_write_refused", proposal_id=proposal["id"])
        text = f"Proposal {proposal['id']} created; send a request with an id to see it"
        return ClientReply(tool_response(request, text, is_error=True))
    action = "Created" if created else "Reusing open"
    command = shlex.join(
        [
            sys.executable,
            "-m",
            "shared_memory.approval_gate.cli",
            "--config",
            str(config_path.resolve()),
            "approve",
            proposal["id"],
        ]
    )
    checkout = shlex.quote(str(Path(__file__).resolve().parents[2]))
    text = (
        f"{action} approval proposal {proposal['id']}. "
        "Nothing was written. Present this proposal to the owner; "
        f"project: {proposal['project']}; expires: {proposal['expires_at']}; "
        f"content hash: {proposal['content_hash']}. "
        f"Owner approval command: (cd {checkout} && {command})"
    )
    return ClientReply(tool_response(request, text, proposal_id=proposal["id"]))


async def _run_proxy(config: Config, config_path: Path) -> int:
    prepare(config)
    native = await start_native(config)
    client = NativeClient(native)
    loop = asyncio.get_running_loop()
    client_in = asyncio.StreamReader(limit=MESSAGE_LIMIT)
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(client_in), sys.stdin)
    transport, protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    client_out = asyncio.StreamWriter(transport, protocol, None, loop)

    async def write_client(data: bytes) -> None:
        client_out.write(data)
        await client_out.drain()

    async def emit(message: dict[str, Any]) -> None:
        await write_client((json.dumps(message, ensure_ascii=False) + "\n").encode())

    def native_call(meta: dict[str, Any]) -> NativeCall:
        async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            return structured_data(await client.call_tool(name, arguments, meta), name)

        return call

    async def relay_write(message: dict[str, Any]) -> None:
        try:
            reply = await handle_write(message, config, config_path, native_call(envelope(message)))
        except OSError as error:
            reply = ClientReply(tool_response(message, f"Approval gate could not process bm_write: {error}", True))
        try:
            match reply:
                case ClientReply(response):
                    await emit(response)
                case NativeRequest(request):
                    await client.send(request)
        except (ValueError, OSError) as error:
            warn(f"Could not relay the bm_write reply: {error}")

    # Each write runs in its own task so its native lookups do not hold up later client messages.
    writes: set[asyncio.Task[None]] = set()

    async def client_to_native() -> None:
        try:
            while line := await client_in.readline():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    warn(f"Dropping malformed client message: {error}")
                    continue
                batch = isinstance(payload, list)
                for message in payload if batch else [payload]:
                    if not isinstance(message, dict):
                        continue
                    if message.get("method") != "tools/call":
                        await client.send(message)
                        continue
                    params = message.get("params")
                    if not isinstance(params, dict) or params.get("name") not in ALLOWED_TOOLS:
                        await emit(tool_response(message, "Tool is not allowed by the approval gate", is_error=True))
                        continue
                    name = params["name"]
                    if name == "bm_project":
                        arguments = params.get("arguments")
                        if not isinstance(arguments, dict) or arguments.get("command") not in ("list", "recent"):
                            await emit(tool_response(message, "bm_project only allows list and recent", is_error=True))
                            continue
                    if name != "bm_write":
                        await client.send(message)
                        continue
                    if batch:
                        await emit(tool_response(message, "Batched bm_write calls are not allowed", is_error=True))
                        continue
                    task = asyncio.create_task(relay_write(message))
                    writes.add(task)
                    task.add_done_callback(writes.discard)
        except (ValueError, OSError) as error:
            warn(f"Client-to-native relay stopped: {error}")
        finally:
            # A forwarded temporary write must reach the native server before its stdin closes.
            await asyncio.gather(*writes, return_exceptions=True)
            try:
                client.stdin.close()
            except OSError as error:
                warn(f"Could not close native stdin: {error}")

    async def forward(line: bytes, reply: Any) -> None:
        if isinstance(reply, dict) and "method" not in reply:
            result = reply.get("result")
            if isinstance(result, dict) and isinstance(result.get("tools"), list):
                result["tools"] = [
                    tool for tool in result["tools"] if isinstance(tool, dict) and tool.get("name") in ALLOWED_TOOLS
                ]
                await emit(reply)
                return
        await write_client(line)

    requests = asyncio.create_task(client_to_native())
    try:
        await client.relay(forward)
    except (ValueError, OSError) as error:
        warn(f"Native-to-client relay stopped: {error}")
    status = await native.wait()
    requests.cancel()
    for task in writes:
        task.cancel()
    return status


def run_proxy(config: Config, config_path: Path) -> int:
    return asyncio.run(_run_proxy(config, config_path))


def main(argv: list[str] | None = None) -> int:
    parser = configargparse.ArgumentParser(description=__doc__)
    add_config_argument(parser)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    return run_proxy(config, args.config)


if __name__ == "__main__":
    raise SystemExit(main())
