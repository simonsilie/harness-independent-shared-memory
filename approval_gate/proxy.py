"""Transparent stdio MCP proxy that gates durable bm_write calls."""

import json
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Any
from uuid import uuid4

import configargparse

from . import ProposalError
from .config import Config, load_config
from .native import warn
from .proposals import audit, create_or_reuse, prepare
from .writes import NativeCall, temporary_arguments

_stdout_lock = threading.Lock()


def emit(message: dict[str, Any]) -> None:
    with _stdout_lock:
        sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def tool_response(
    request: dict[str, Any], text: str, is_error: bool = False, proposal_id: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if proposal_id is not None:
        result["structuredContent"] = {"result": {"proposal_id": proposal_id, "message": text}}
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": result,
    }


def _is_write(message: Any) -> bool:
    return (
        isinstance(message, dict)
        and message.get("method") == "tools/call"
        and isinstance(message.get("params"), dict)
        and message["params"].get("name") == "bm_write"
    )


def handle_write(request: dict[str, Any], config: Config, config_path: Path, call_native: NativeCall) -> dict[str, Any]:
    arguments = request["params"].get("arguments", {})
    if not isinstance(arguments, dict):
        return tool_response(request, "bm_write arguments must be an object", is_error=True)
    try:
        temporary = temporary_arguments(arguments, call_native)
        if temporary is not None:
            return {**request, "params": {**request["params"], "arguments": temporary}}
        proposal, created = create_or_reuse(config, arguments, call_native)
    except ProposalError as error:
        audit(config, "write_refused", reason=str(error), id=request.get("id"))
        return tool_response(request, str(error), is_error=True)
    if request.get("id") is None:
        audit(config, "unidentified_write_refused", proposal_id=proposal["id"])
        return tool_response(request, f"Proposal {proposal['id']} created; send a request with an id to see it", True)
    action = "Created" if created else "Reusing open"
    command = shlex.join(
        [sys.executable, "-m", "approval_gate.cli", "--config", str(config_path.resolve()), "approve", proposal["id"]]
    )
    checkout = shlex.quote(str(Path(__file__).resolve().parents[1]))
    text = (
        f"{action} approval proposal {proposal['id']}. "
        "Nothing was written. Present this proposal to the owner; "
        f"project: {proposal['project']}; expires: {proposal['expires_at']}; "
        f"content hash: {proposal['content_hash']}. "
        f"Owner approval command: (cd {checkout} && {command})"
    )
    return tool_response(request, text, proposal_id=proposal["id"])


def run_proxy(config: Config, config_path: Path) -> int:
    prepare(config)
    environment = os.environ | (config.env or {})
    native = subprocess.Popen(
        config.native_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=environment,
    )
    assert native.stdin is not None and native.stdout is not None
    internal_id_prefix = f"approval-gate-{uuid4().hex}-"
    pending: dict[str, Queue[dict[str, Any]]] = {}
    pending_lock = threading.Lock()

    def send_native(message: dict[str, Any]) -> None:
        native.stdin.write(json.dumps(message) + "\n")
        native.stdin.flush()

    def call_native(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        request_id = f"{internal_id_prefix}{uuid4().hex}"
        replies: Queue[dict[str, Any]] = Queue(maxsize=1)
        with pending_lock:
            pending[request_id] = replies
        try:
            send_native(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": {**arguments, "output_format": "json"}},
                }
            )
            reply = replies.get(timeout=20)
        except Empty as error:
            raise ProposalError(f"Native {name} timed out.") from error
        finally:
            with pending_lock:
                pending.pop(request_id, None)
        if "error" in reply:
            raise ProposalError(f"Native {name} failed: {reply['error']}")
        result = reply.get("result")
        if not isinstance(result, dict):
            raise ProposalError(f"Native {name} did not return a tool result.")
        if result.get("isError"):
            raise ProposalError(f"Native {name} refused: {result.get('content')}")
        data = result.get("structuredContent")
        if not isinstance(data, dict):
            raise ProposalError(f"Native {name} did not return structured data.")
        data = data.get("result", data)
        if not isinstance(data, dict):
            raise ProposalError(f"Native {name} did not return an object.")
        return data

    def client_to_native() -> None:
        try:
            for line in sys.stdin:
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as error:
                    warn(f"Dropping malformed client message: {error}")
                    continue
                if isinstance(message, list):
                    writes = [item for item in message if _is_write(item)]
                    if writes:
                        for item in writes:
                            emit(tool_response(item, "Batched bm_write calls are not allowed", is_error=True))
                        for item in message:
                            if isinstance(item, dict) and not _is_write(item):
                                send_native(item)
                        continue
                if _is_write(message) and isinstance(message, dict):
                    response = handle_write(message, config, config_path, call_native)
                    if "result" in response:
                        emit(response)
                    else:
                        send_native(response)
                    continue
                native.stdin.write(line)
                native.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as error:
            warn(f"Client-to-native relay stopped: {error}")
        finally:
            try:
                native.stdin.close()
            except OSError as error:
                warn(f"Could not close native stdin: {error}")

    def native_to_client() -> None:
        try:
            for line in native.stdout:
                try:
                    reply = json.loads(line)
                except json.JSONDecodeError:
                    reply = None
                if isinstance(reply, dict) and "method" not in reply:
                    request_id = reply.get("id")
                    if isinstance(request_id, str) and request_id.startswith(internal_id_prefix):
                        with pending_lock:
                            replies = pending.pop(request_id, None)
                            if replies is not None:
                                replies.put_nowait(reply)
                        continue
                with _stdout_lock:
                    sys.stdout.write(line)
                    sys.stdout.flush()
        except (ValueError, OSError) as error:
            warn(f"Native-to-client relay stopped: {error}")

    threading.Thread(target=client_to_native, daemon=True).start()
    threading.Thread(target=native_to_client, daemon=True).start()
    return native.wait()


def main(argv: list[str] | None = None) -> int:
    parser = configargparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json"), env_var="SHARED_MEMORY_APPROVAL_CONFIG"
    )
    args = parser.parse_args(argv)
    config = load_config(args.config)
    return run_proxy(config, args.config)


if __name__ == "__main__":
    raise SystemExit(main())
