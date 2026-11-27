import asyncio
import hashlib
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from evaluation.clients import behavior, lifecycle
from evaluation.indexing_cost import run as indexing

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "module",
    [
        "evaluation.clients.behavior",
        "evaluation.clients.lifecycle",
        "evaluation.indexing_cost.run",
        "evaluation.claude.run",
        "evaluation.codex.run",
        "evaluation.opencode.run",
        "evaluation.recovery.run",
        "evaluation.evidence.run",
    ],
)
def test_import_has_no_filesystem_process_or_umask_side_effects(module, tmp_path):
    script = """
import importlib
import os
import sys
from unittest.mock import patch

def audit(event, args):
    if event == "open":
        _, mode, flags = args
        assert not (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)), args
    assert event not in {"os.mkdir", "os.remove", "os.rename", "subprocess.Popen", "os.system"}, (event, args)

sys.addaudithook(audit)
before = sys.path.copy()
with patch("os.umask", side_effect=AssertionError("Import changed umask")):
    importlib.import_module(sys.argv[1])
assert sys.path == before
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, module],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []


class CodexProcess:
    def __init__(self):
        self.stdin = self
        self.stdout = self
        self.messages = asyncio.Queue()

    def write(self, data):
        request = json.loads(data)
        if "id" not in request:
            return
        method = request["method"]
        result = {"thread": {"id": "isolated-thread"}} if method == "thread/start" else {}
        self.messages.put_nowait({"id": request["id"], "result": result})
        if method == "turn/start":
            prompt = request["params"]["input"][0]["text"]
            self.messages.put_nowait(
                {"method": "item/completed", "params": {"item": {"type": "agentMessage", "text": prompt}}}
            )
            self.messages.put_nowait({"method": "turn/completed", "params": {"turn": {"status": "completed"}}})

    async def readline(self):
        await asyncio.sleep(0)
        return json.dumps(await self.messages.get()).encode() + b"\n"

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait(self):
        return 0


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_client_runs_keep_prompts_and_results_separate(client, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    prompts_a, prompts_b = ["first input", "first follow-up"], ["second input"]

    async def spawn(*args, **kwargs):
        return CodexProcess()

    def run(command, **kwargs):
        events = [{"type": "text", "part": {"text": command[-1]}}] if "run" in command else []
        return SimpleNamespace(returncode=0, stdout="\n".join(map(json.dumps, events)), stderr="")

    async def evaluate():
        if client == "codex":
            return await asyncio.gather(
                behavior.codex({}, first, prompts_a),
                behavior.codex({}, second, prompts_b),
            )
        return await asyncio.gather(
            asyncio.to_thread(behavior.opencode, {}, first, prompts_a),
            asyncio.to_thread(behavior.opencode, {}, second, prompts_b),
        )

    process = SimpleNamespace(poll=lambda: None, terminate=lambda: None, wait=lambda *args: 0)
    with (
        patch.object(behavior.asyncio, "create_subprocess_exec", spawn),
        patch.object(behavior.subprocess, "Popen", return_value=process),
        patch.object(behavior.subprocess, "run", side_effect=run),
        patch.object(behavior.socket, "create_connection", return_value=nullcontext()),
    ):
        results = asyncio.run(evaluate())

    assert [[answer.strip() for _, answer in turns] for turns in results] == [prompts_a, prompts_b]
    assert json.loads((first / f"{client}-turn-0.json").read_text())[1].strip() == prompts_a[0]
    assert json.loads((second / f"{client}-turn-0.json").read_text())[1].strip() == prompts_b[0]
    assert (first / f"{client}-turn-1.json").exists()
    assert not (second / f"{client}-turn-1.json").exists()
    assert behavior.PROMPTS[0] == "Antworte nur mit bereit."


class MemorySession:
    def __init__(self, env, unused):
        self.root = Path(env["BASIC_MEMORY_CONFIG_DIR"]).parent / behavior.ROOT.name

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def initialize(self):
        pass

    async def call_tool(self, tool, args):
        path = self.root / args["identifier"]
        checksum = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        conflict = tool == "bm_write" and args.get("expected_checksum", checksum) != checksum
        if conflict:
            value = "REVISION_CONFLICT"
        else:
            if tool == "bm_write":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(args["content"])
            value = {"content": path.read_text(), "checksum": hashlib.sha256(path.read_bytes()).hexdigest()}
        return SimpleNamespace(
            is_error=conflict,
            content=[SimpleNamespace(type="text", text=json.dumps(value))],
            model_dump=lambda **kwargs: value,
        )


@asynccontextmanager
async def memory_transport(params, **kwargs):
    yield params.env, None


def test_lifecycle_runs_keep_outputs_and_client_selection_separate(tmp_path):
    async def run_client(env, out, prompts, **kwargs):
        root = Path(env["BASIC_MEMORY_CONFIG_DIR"]).parent / behavior.ROOT.name
        continuation = root / "temporary/continuation.md"

        def save(path, metadata, body):
            path.write_text("---\n" + yaml.safe_dump(metadata) + "---\n" + body)

        now = datetime.now(timezone.utc).isoformat()
        if len(prompts) == 1:
            token = prompts[0].split("lautet ", 1)[1].split(".", 1)[0]
            save(
                continuation, {"kind": "temporary", "status": "active", "last_activity": now}, token + " Ergebnisdatei"
            )
            return [([], prompts[0])]

        tokens = {
            name: (root / f"temporary/{name}.md").read_text().split("Fortsetzungshinweis: ", 1)[1].split(".", 1)[0]
            for name in ("expired", "extended")
        }
        _, body = lifecycle.note(env, "temporary/continuation.md")
        turns = [([("bm_read", {})], body + tokens["extended"])]
        for name in ("expired", "boundary", "extension-ended", "completed"):
            meta, text = lifecycle.note(env, f"temporary/{name}.md")
            save(root / f"temporary/{name}.md", meta | {"status": "archived"}, text.split("---", 2)[2])
        for index in range(1, 6):
            if index == 4:
                turns.append(([], tokens["expired"]))
                continue
            name = "extended" if index == 2 else "expired" if index == 5 else "continuation"
            meta, text = lifecycle.note(env, f"temporary/{name}.md")
            meta["last_activity"] = now
            if index == 2:
                meta["extended_until"] = prompts[index].split("bis ", 1)[1].removesuffix(".")
            if index == 3:
                meta.update(status="archived", archive_reason="completed")
            if index == 5:
                meta.update(
                    status="active", archived_at=None, archive_reason=None, completed_at=None, extended_until=None
                )
            path = root / f"temporary/{name}.md"
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            save(path, meta, text.split("---", 2)[2])
            turns.append(([("bm_write", {"content": path.read_text(), "expected_checksum": checksum})], "updated"))
        return turns

    def run_opencode(*args, **kwargs):
        return asyncio.run(run_client(*args, **kwargs))

    first, second = tmp_path / "first", tmp_path / "second"
    with (
        patch.object(lifecycle, "snapshot", return_value={}),
        patch.object(behavior, "stdio_client", memory_transport),
        patch.object(behavior, "ClientSession", MemorySession),
        patch.object(behavior, "codex", run_client),
        patch.object(behavior, "opencode", run_opencode),
    ):
        asyncio.run(lifecycle.main(first, clients=["codex"]))
        before = {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        asyncio.run(lifecycle.main(second, clients=["opencode"]))

    assert {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()} == before
    assert json.loads((first / "result.json").read_text())["clients_passed"] == ["codex"]
    assert json.loads((second / "result.json").read_text())["clients_passed"] == ["opencode"]
    capture_a = json.loads((first / "codex/capture.json").read_text())
    capture_b = json.loads((second / "opencode/capture.json").read_text())
    assert capture_a != capture_b


def test_indexing_runs_keep_inputs_and_results_separate(tmp_path):
    def prepare(root, label):
        root.mkdir()
        source = label.encode()
        (root / "harness-independent-shared-memory.md").write_bytes(source)
        revision = "sha256:" + hashlib.sha256(source).hexdigest()
        (root / "corpus").mkdir()
        for index in range(20):
            (root / "corpus" / f"{index}.md").write_text(
                f'---\nreview_status: "accepted"\nsource_revision: "{revision}"\n---\n{label}-{index}\n'
            )
        (root / ".state").mkdir()
        (root / ".state/config.json").write_text("{}")

    def run(command, **kwargs):
        stdout = "test-version\n" if "--version" in command else json.dumps({"results": [{}] * 20})
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    def spawn(command, *, env, stdout, stderr, **kwargs):
        (Path(env["BASIC_MEMORY_CONFIG_DIR"]) / "memory.db").write_bytes(env["BASIC_MEMORY_HOME"].encode())
        return SimpleNamespace(pid=123, returncode=None)

    first_root, second_root = tmp_path / "source-a", tmp_path / "source-b"
    prepare(first_root, "first")
    prepare(second_root, "second")
    first, second = tmp_path / "first", tmp_path / "second"
    with (
        patch.object(indexing.subprocess, "run", side_effect=run),
        patch.object(indexing.subprocess, "Popen", side_effect=spawn),
        patch.object(indexing.os, "wait4", return_value=(123, 0, SimpleNamespace(ru_maxrss=1024))),
    ):
        with patch.object(indexing, "ROOT", first_root):
            indexing.main(first)
        before = {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        with patch.object(indexing, "ROOT", second_root):
            indexing.main(second)

    assert {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()} == before
    assert (first / "corpus/0.md").read_text().endswith("first-0\n")
    assert (second / "corpus/0.md").read_text().endswith("second-0\n")
    assert json.loads((first / "corpus-hashes.json").read_text()) != json.loads(
        (second / "corpus-hashes.json").read_text()
    )
    for out in (first, second):
        summary = json.loads((out / "result.json").read_text())
        assert summary["notes"] == 20 and summary["corpus_unchanged"]
        config = json.loads((out / "state-search/config.json").read_text())
        assert config["projects"]["main"]["path"] == str(out / "corpus")
