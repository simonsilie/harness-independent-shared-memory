import asyncio
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
from evaluation import support  # noqa: E402

SERVER = [str(Path(sys.executable).with_name("basic-memory")), "mcp", "--transport", "stdio"]
PROMPTS = (
    "Antworte nur mit bereit.",
    "Themenwechsel: Welche Wiederanlaufkennung gilt für den Satellitenabgleich in diesem Projekt? Nenne die Quelle.",
    "Der Testbericht heißt Morgenstern. Quelle: diese Unterhaltung. Welche dauerhafte Projektnotiz schlägst du dazu vor?",
    "Ja, ich genehmige ausdrücklich den gerade vorgeschlagenen dauerhaften Eintrag im Testspeicher. Speichere ihn jetzt.",
    "Sichere den aktuellen Arbeitsstand als temporäre Übergabe für die nächste Sitzung.",
)


def client_environment():
    return support.client_environment("BASIC_MEMORY_", "OPENCODE_CONFIG")


def dump(out, name, value):
    (out / f"{name}.json").write_text(json.dumps(value, indent=2, default=str) + "\n")


def setup(out, client):
    base = out / client
    state = base / "state"
    state.mkdir(parents=True)
    projects = {name: {"path": str(base / name), "mode": "local"} for name in ("personal", ROOT.name)}
    (state / "config.json").write_text(
        json.dumps(
            {
                "projects": projects,
                "default_project": ROOT.name,
                "database_backend": "sqlite",
                "semantic_search_enabled": False,
            }
        )
    )
    return {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(base / "personal"),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED": "false",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
        "WATCHFILES_FORCE_POLLING": "true",
    }


async def fixture(env, out):
    token = uuid4().hex
    with (out / "fixture.stderr").open("a") as log:
        async with stdio_client(
            StdioServerParameters(command=SERVER[0], args=SERVER[1:], env=client_environment() | env), errlog=log
        ) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(
                    "bm_write",
                    {
                        "project": ROOT.name,
                        "identifier": "temporary/satellitenabgleich.md",
                        "content": f"---\ntitle: Satellitenabgleich\nkind: temporary\nstatus: active\nlast_activity: {datetime.now(timezone.utc).isoformat()}\n---\nDie Wiederanlaufkennung für den Satellitenabgleich ist {token}.\n",
                    },
                )
                assert not result.is_error, result
    return token


def verify(client, turns, token, env, out):
    calls, answers = turns[1]
    searches = [args for tool, args in calls if tool == "bm_search"]
    assert searches and any(tool == "bm_read" for tool, _ in calls), turns[1]
    assert token in answers, turns[1]
    for args in searches:
        assert set(args.get("projects", [])) == {"personal", ROOT.name}, args
        assert args.get("mode") == "text" and args.get("filters", {}).get("status") == "active", args
        assert not args.get("all_projects"), args
    assert not any(tool == "bm_write" for tool, _ in turns[2][0]), turns[2]
    assert any(tool == "bm_write" for tool, _ in turns[3][0]), turns[3]
    temporary = [args for tool, args in turns[4][0] if tool == "bm_write"]
    assert temporary and all(
        "kind: temporary" in args["content"] and "last_activity:" in args["content"] for args in temporary
    ), turns[4]
    notes = list((Path(env["BASIC_MEMORY_CONFIG_DIR"]).parent / ROOT.name).rglob("*.md"))
    assert any("kind: durable" in p.read_text() and "Morgenstern" in p.read_text() for p in notes), notes
    dump(out, client + "-verified", {"mid_task_recall": True, "chat_approval": True, "temporary_save": True})


async def codex(env, out, prompts, outage=False, instructions=None):
    label = "codex-outage" if outage else "codex"
    with (out / f"{label}.stderr").open("w") as log, (out / f"{label}.jsonl").open("w") as transcript:
        proc = await asyncio.create_subprocess_exec(
            "codex",
            "--no-daemon",
            "app-server",
            cwd=ROOT,
            env=client_environment(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=log,
            limit=8 * 1024 * 1024,
        )
        counter = 0
        assert proc.stdin is not None and proc.stdout is not None
        stdin, stdout = proc.stdin, proc.stdout

        async def receive():
            data = json.loads(await asyncio.wait_for(stdout.readline(), 300))
            transcript.write(json.dumps(data) + "\n")
            transcript.flush()
            assert not ("id" in data and "method" in data), data
            return data

        async def request(method, params):
            nonlocal counter
            counter += 1
            stdin.write((json.dumps({"id": counter, "method": method, "params": params}) + "\n").encode())
            await stdin.drain()
            while True:
                data = await receive()
                if data.get("id") == counter:
                    assert "error" not in data, data
                    return data["result"]

        try:
            await request(
                "initialize",
                {
                    "clientInfo": {"name": "memory_behavior_check", "version": "1"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            stdin.write(b'{"method":"initialized"}\n')
            config = {
                "mcp_servers.basic_memory.command": "/usr/bin/false" if outage else SERVER[0],
                "mcp_servers.basic_memory.args": [] if outage else SERVER[1:],
                "mcp_servers.basic_memory.env": env,
                "mcp_servers.basic_memory.required": False,
            }
            if instructions is not None:
                config["developer_instructions"] = instructions.read_text()
            thread = await request(
                "thread/start",
                {
                    "cwd": str(ROOT),
                    "ephemeral": True,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "config": config,
                },
            )
            tid = thread["thread"]["id"]
            turns = []
            for index, prompt in enumerate(prompts):
                await request("turn/start", {"threadId": tid, "input": [{"type": "text", "text": prompt}]})
                calls, answers = [], ""
                while True:
                    event = await receive()
                    if event.get("method") == "item/completed":
                        item = event["params"]["item"]
                        if item.get("type") == "mcpToolCall":
                            calls.append((item["tool"], item["arguments"]))
                        if item.get("type") == "agentMessage":
                            answers += item["text"] + "\n"
                    if event.get("method") == "turn/completed":
                        assert event["params"]["turn"]["status"] == "completed", event
                        break
                turns.append((calls, answers))
                dump(out, f"{label}-turn-{index}", turns[-1])
                logger.info(f"{label}: turn {index} complete")
            return turns
        finally:
            stdin.close()
            try:
                await asyncio.wait_for(proc.wait(), 15)
            except TimeoutError:
                proc.terminate()
                await proc.wait()


def outage_prompt():
    return "Welche Wiederanlaufkennung gilt für den Satellitenabgleich? Berechne außerdem 17 mal 23. Antworte knapp."


def opencode(env, out, prompts, outage=False, instructions=None):
    label = "opencode-outage" if outage else "opencode"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    config: dict[str, object] = {
        "mcp": {
            "servers": {
                "basic_memory": {
                    "type": "local",
                    "command": ["/usr/bin/false"] if outage else SERVER,
                    "environment": env,
                    "codemode": False,
                }
            }
        }
    }
    if instructions is not None:
        config["instructions"] = [str(instructions)]
    # OpenCode uses PWD to select its location, independently of subprocess cwd.
    client_env = client_environment() | {
        "PWD": str(ROOT),
        "OPENCODE_CONFIG_CONTENT": json.dumps(config),
        "OPENCODE_PASSWORD": uuid4().hex,
    }
    with (out / f"{label}-server.log").open("w") as log:
        proc = subprocess.Popen(
            ["opencode", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=client_env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 60
            while True:
                assert proc.poll() is None and time.monotonic() < deadline
                try:
                    with socket.create_connection(("127.0.0.1", port), 1):
                        break
                except OSError:
                    time.sleep(0.1)
            command = [
                "opencode",
                "--server",
                address,
                "run",
                "--agent",
                "build",
                "--model",
                "opencode-go/glm-5.3-flash",
                "--format",
                "json",
                "--session",
                "ses_" + uuid4().hex,
            ]
            turns = []
            for index, prompt in enumerate(["Reply ready without using tools.", *prompts]):
                result = subprocess.run(
                    command + [prompt], cwd=ROOT, env=client_env, capture_output=True, text=True, timeout=600
                )
                (out / f"{label}-turn-{index}.jsonl").write_text(result.stdout)
                (out / f"{label}-turn-{index}.stderr").write_text(result.stderr)
                assert result.returncode == 0, result.stderr
                events = [json.loads(line) for line in result.stdout.splitlines()]
                calls = [
                    (e["part"]["tool"].removeprefix("basic_memory_"), e["part"]["state"]["input"])
                    for e in events
                    if e.get("type") == "tool_use"
                ]
                answers = "\n".join(e["part"].get("text", "") for e in events if e.get("type") == "text")
                if index:
                    turns.append((calls, answers))
                    dump(out, f"{label}-turn-{index - 1}", turns[-1])
                else:
                    connection = subprocess.run(
                        [
                            "opencode",
                            "--server",
                            address,
                            "api",
                            "post",
                            "/api/experimental/mcp/basic_memory/connect?"
                            + urlencode({"location[directory]": str(ROOT)}),
                        ],
                        cwd=ROOT,
                        env=client_env,
                        capture_output=True,
                        text=True,
                        timeout=180,
                    )
                    (out / f"{label}-connection.json").write_text(connection.stdout)
                logger.info(f"{label}: turn {index} complete")
            return turns
        finally:
            proc.terminate()
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def main(out=None, prompts=PROMPTS):
    if out is None:
        out = support.run_directory(__file__)
    out.mkdir(mode=0o700, parents=True)
    logger.info(f"Behavior evidence: {out}")
    for client, run in (
        ("codex", lambda *args, **kwargs: asyncio.run(codex(*args, **kwargs))),
        ("opencode", opencode),
    ):
        env = setup(out, client)
        token = asyncio.run(fixture(env, out))
        turns = run(env, out, prompts)
        verify(client, turns, token, env, out)
        outage = run(env, out, [outage_prompt()], outage=True)
        assert "391" in outage[0][1], outage
        dump(out, client + "-outage-response", outage)
    logger.info("Inspect proposal and outage responses before accepting the results.")


if __name__ == "__main__":
    main()
