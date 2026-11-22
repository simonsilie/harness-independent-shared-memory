import contextlib
import hashlib
import importlib.util
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evaluation.opencode.inventory import ALLOWED_TOOLS, verify_inventory

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "evaluation/opencode"


def inventory_events() -> list[dict[str, Any]]:
    return [
        {"kind": "request.context", "toolNames": sorted(ALLOWED_TOOLS)},
        {
            "kind": "request.context.snapshot",
            "tools": dict.fromkeys(ALLOWED_TOOLS, {}),
            "system": ["Do not use filesystem tools."],
            "mcp": {"data": [{"name": "basic_memory", "status": {"status": "connected"}}]},
        },
    ]


class OpenCodeChecks(unittest.TestCase):
    source = b"Keep SQLite local.\n"
    source_revision = "sha256:" + hashlib.sha256(source).hexdigest()

    def note(self, record_id, stale=False):
        metadata = {
            "id": record_id,
            "permalink": record_id,
            "review_status": "accepted",
            "source_revision": "stale:" if stale else self.source_revision,
        }
        frontmatter = "\n".join(f"{key}: {json.dumps(value)}" for key, value in metadata.items())
        return f"---\n{frontmatter}\n---\n\nKeep SQLite local.\n"

    def check_script(self, script, executions, response="Keep SQLite local."):
        events = inventory_events() + executions
        out = ROOT / "unused-test-run"
        files = {
            out / "client-response.txt": json.dumps(
                {"sessionID": "test-session", "type": "text", "part": {"text": response}}
            ),
            ROOT / "evaluation/opencode/runs/test-session/events.jsonl": "\n".join(map(json.dumps, events)),
            out / "corpus-before.json": "{}",
            out / "corpus-after.json": "{}",
            out / "prompt.txt": "Plan how to work across two laptops with a live SQLite database.",
            out / "client-version.json": '{"basic_memory": "Basic Memory version: 1.0.0"}',
        }
        corpus = {
            ROOT / "evaluation/corpus" / f"memory-{number:02d}.md": self.note(f"memory-{number:02d}")
            for number in range(1, 21)
        }
        files.update(corpus)
        reads = Path.read_text
        byte_reads = Path.read_bytes
        globs = Path.glob
        writes = {}

        def read(path, *args, **kwargs):
            return files[path] if path in files else reads(path, *args, **kwargs)

        with (
            patch.object(sys, "argv", [script, str(out)]),
            patch.object(Path, "read_text", read),
            patch.object(
                Path,
                "read_bytes",
                lambda path: (
                    self.source
                    if path == ROOT / "evaluation/harness-independent-shared-memory.md"
                    else byte_reads(path)
                ),
            ),
            patch.object(
                Path,
                "glob",
                lambda path, pattern: (
                    iter(corpus) if path == ROOT / "evaluation/corpus" and pattern == "*.md" else globs(path, pattern)
                ),
            ),
            patch.object(
                Path, "write_text", lambda path, text: writes.update({path.relative_to(out).as_posix(): text})
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            runpy.run_path(str(SCRIPTS / script), run_name="__main__")
        return writes

    def startup_calls(self, stale=False):
        note = self.note("memory-20", stale=stale)
        calls: list[dict[str, Any]] = []
        for tool, output in [
            ("basic_memory_bm_search", {"results": [{"permalink": "memory-20"}]}),
            ("basic_memory_bm_read", note),
        ]:
            calls.extend(
                [
                    {"kind": "tool.execute.before", "tool": tool, "callID": tool},
                    {
                        "kind": "tool.execute.completed",
                        "tool": tool,
                        "callID": tool,
                        "result": {"output": output},
                    },
                ]
            )
        return calls

    def test_inventory_rejects_missing_capture_and_extra_tools(self):
        with self.assertRaises(ValueError):
            verify_inventory([])
        events = inventory_events()
        events[0]["toolNames"].append("basic_memory_bm_write")
        with self.assertRaises(ValueError):
            verify_inventory(events)

    def test_startup_rejects_no_retrieval(self):
        with self.assertRaisesRegex(AssertionError, "No startup search"):
            self.check_script("verify_startup.py", [])

    def test_startup_rejects_stale_guidance(self):
        with self.assertRaisesRegex(AssertionError, "Stale SQLite guidance"):
            self.check_script("verify_startup.py", self.startup_calls(stale=True))

    def test_startup_requires_relevant_paired_reads(self):
        calls = self.startup_calls()
        with self.assertRaisesRegex(AssertionError, "No startup read"):
            self.check_script("verify_startup.py", calls[:2])
        writes = self.check_script("verify_startup.py", calls)
        self.assertEqual(json.loads(writes["startup-result.json"])["reads"], 1)

    def test_startup_accepts_text_formatted_search_evidence(self):
        calls = self.startup_calls()
        calls[1]["result"]["output"] = {"result": "- memory-20.md | SQLite backup safety | score -4.5"}
        self.check_script("verify_startup.py", calls)
        calls[1]["result"]["output"] = {"result": "No results"}
        with self.assertRaisesRegex(AssertionError, "did not retrieve"):
            self.check_script("verify_startup.py", calls)

    def test_runner_stops_without_plugin_confirmation(self):
        self.run_runner(captured=False)

    def test_recall_does_not_claim_served_revisions_without_reads(self):
        questions = json.loads((ROOT / "evaluation/questions.json").read_text())
        calls, results = [], []
        for question in questions:
            query = question["id"]
            arguments = {"query": query, "mode": "text"}
            calls.extend(
                [
                    {
                        "kind": "tool.execute.before",
                        "tool": "basic_memory_bm_search",
                        "callID": query,
                        "time": "2026-11-14T11:00:00Z",
                        "input": arguments,
                    },
                    {
                        "kind": "tool.execute.completed",
                        "tool": "basic_memory_bm_search",
                        "callID": query,
                        "time": "2026-11-14T11:00:01Z",
                        "result": {"output": {"results": [{"permalink": "memory-20"}]}},
                    },
                ]
            )
            results.append(
                {
                    "question_id": query,
                    "query": query,
                    "mode": "text",
                    "retrieved_ids": ["memory-20"],
                    "recognized_missing_evidence": False,
                }
            )
        writes = self.check_script("verify.py", calls, json.dumps(results))
        self.assertEqual(set(writes), {"results.json", "tool-calls.json", "verification-summary.json"})
        self.assertEqual(json.loads(writes["results.json"]), results)
        summary = json.loads(writes["verification-summary.json"])
        self.assertFalse(summary["served_source_revisions_verified"])
        self.assertEqual(summary["returned_ids_without_verified_source_revision"], ["memory-20"])

    def test_verify_only_checks_inventory_without_sending_questions(self):
        self.run_runner(captured=True)

    def test_questions_are_sent_only_after_inventory_confirmation(self):
        self.run_runner(captured=True, verify_only=False)

    def run_runner(self, captured, verify_only=True):
        spec = importlib.util.spec_from_file_location("opencode_runner", SCRIPTS / "run.py")
        assert spec is not None and spec.loader is not None
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            root = Path(temporary)
            (root / "evaluation/opencode").mkdir(parents=True)
            (root / "evaluation/opencode/opencode.json").write_text("{}")
            (root / "evaluation/corpus").mkdir()
            (root / "evaluation/questions.json").write_text("[]")
            (root / "evaluation/opencode/runs").mkdir(parents=True)
            setattr(runner, "ROOT", root)
            setattr(runner, "OUT", root / "evaluation/opencode/runs/check")

            def preflight(command, **kwargs):
                if "api" in command:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[-1] != "Check readiness.":
                    self.assertTrue(captured)
                    self.assertTrue((runner.OUT / "effective-tools.json").exists())
                    return subprocess.CompletedProcess(command, 0, "", "")
                session = command[command.index("--session") + 1]
                events = inventory_events()
                if captured:
                    events.append({"kind": "request.preflight"})
                (root / "evaluation/opencode/runs" / session / "events.jsonl").write_text(
                    "\n".join(map(json.dumps, events))
                )
                return subprocess.CompletedProcess(command, 1, "", "Preflight stopped")

            with (
                patch.object(sys, "argv", ["run.py"] + (["--verify-only"] if verify_only else [])),
                patch.object(runner, "versions", return_value={}),
                patch.object(runner.socket, "socket") as socket,
                patch.object(runner.socket, "create_connection"),
                patch.object(runner.subprocess, "Popen") as server,
                patch.object(runner.subprocess, "run", side_effect=preflight) as run,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                socket.return_value.__enter__.return_value.getsockname.return_value = (
                    "127.0.0.1",
                    5000,
                )
                server.return_value.poll.return_value = None
                if captured:
                    runner.main()
                    self.assertTrue((runner.OUT / "effective-tools.json").exists())
                else:
                    with self.assertRaisesRegex(ValueError, "did not confirm"):
                        runner.main()
                config = json.loads(server.call_args.kwargs["env"]["OPENCODE_CONFIG_CONTENT"])
                self.assertEqual(config["plugins"], [{"package": str(root / "evaluation/opencode/eval-capture")}])
                self.assertEqual(run.call_count, 3 if verify_only or not captured else 4)
                self.assertEqual(run.call_args_list[2].args[0][-1], "Check readiness.")
