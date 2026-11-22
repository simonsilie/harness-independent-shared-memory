import hashlib
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
STARTUP = "--startup" in sys.argv[2:]
ALLOWED_TOOLS = {"mcp__basic_memory__bm_search", "mcp__basic_memory__bm_read"}


def text_of(content):
    return content if isinstance(content, str) else "".join(block["text"] for block in content)


def frontmatter(markdown):
    return dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in markdown.split("---\n", 2)[1].splitlines())
    )


messages = [json.loads(line) for line in (OUT / "events.jsonl").read_text().splitlines() if line.strip()]
init = messages[0]
assert init["type"] == "system" and init["subtype"] == "init"
assert set(init["tools"]) == ALLOWED_TOOLS, init["tools"]
assert any(s["name"] == "basic_memory" and s["status"] == "connected" for s in init["mcp_servers"])
assert not init.get("memory_paths"), "Auto-memory was enabled"
final = messages[-1]
assert final["type"] == "result" and final["subtype"] == "success" and not final["is_error"]
assert final.get("permission_denials") == [], final.get("permission_denials")

uses = {}
results = {}
for message in messages:
    if message["type"] not in ("assistant", "user") or isinstance(message["message"]["content"], str):
        continue
    assert message.get("parent_tool_use_id") is None, "Subagent activity"
    for block in message["message"]["content"]:
        if block["type"] == "tool_use":
            uses[block["id"]] = block
        elif block["type"] == "tool_result":
            results[block["tool_use_id"]] = block
assert set(uses) == set(results), "Unpaired tool calls"
assert all(use["name"] in ALLOWED_TOOLS for use in uses.values()), "Tool outside allowlist"
assert not any(result.get("is_error") for result in results.values()), "Tool errors occurred"

notes = {}
source_revision = (
    "sha256:" + hashlib.sha256((ROOT / "evaluation/harness-independent-shared-memory.md").read_bytes()).hexdigest()
)
for path in (ROOT / "evaluation/corpus").glob("*.md"):
    metadata = frontmatter(path.read_text())
    assert metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision, path
    notes[metadata["permalink"]] = metadata["id"]
assert len(notes) == 20

calls = []
searches = defaultdict(deque)
read_ids = set()
for key, use in uses.items():
    output = text_of(results[key]["content"])
    call = {"id": key, "tool": use["name"], "arguments": use["input"], "output": output}
    if use["name"] == "mcp__basic_memory__bm_search":
        assert STARTUP or use["input"].get("mode") == "text", use["input"]
        parsed = json.loads(output)
        parsed = parsed.get("result", parsed)
        if isinstance(parsed, str):
            # Without output_format="json" the engine returns "- [project/]memory-NN.md | title" lines.
            permalinks = re.findall(r"^- (?:[^/\s]+/)?([^/\s]+)\.md \|", parsed, re.MULTILINE)
        else:
            permalinks = [row["permalink"] for row in parsed["results"]]
        call["ids"] = [notes[permalink] for permalink in permalinks]
        searches[use["input"].get("query")].append(call)
    else:
        metadata = frontmatter(output)
        assert metadata["id"] == notes[metadata["permalink"]], output[:200]
        assert metadata["source_revision"] == source_revision, output[:200]
        read_ids.add(metadata["id"])
    calls.append(call)
assert json.loads((OUT / "corpus-before.json").read_text()) == json.loads((OUT / "corpus-after.json").read_text())
(OUT / "tool-calls.json").write_text(json.dumps(calls, indent=2) + "\n")
executed = Counter(call["tool"].removeprefix("mcp__basic_memory__") for call in calls)

if STARTUP:
    prompt = (OUT / "prompt.txt").read_text().lower() + (OUT / "instructions.txt").read_text().lower()
    assert not any(term in prompt for term in ("memory", "recall", "search")), "Prompt mentions memory retrieval"
    assert any("memory-20" in call.get("ids", []) for call in calls), "SQLite guidance not retrieved"
    assert "memory-20" in read_ids, "SQLite guidance not read"
    outcome = {
        "effective_tools": sorted(init["tools"]),
        "executed_tools": dict(executed),
        "client_response": final["result"],
    }
    (OUT / "startup-result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    logger.info(f"Startup check verified: {dict(executed)}, memory-20 retrieved and read, corpus unchanged.")
    raise SystemExit

# The recorded run prefixed the requested array with one line of prose; accept exactly one fenced block.
fenced = re.findall(r"^```(?:json)?\n(.*?)\n```$", final["result"], re.MULTILINE | re.DOTALL)
declared = json.loads(fenced[0] if len(fenced) == 1 else final["result"])
questions = json.loads((ROOT / "evaluation/questions.json").read_text())
assert [r["question_id"] for r in declared] == [q["id"] for q in questions], "Question order mismatch"
for result in declared:
    call = searches[result["query"]].popleft()
    assert result["mode"] == call["arguments"]["mode"], result["question_id"]
    assert result["retrieved_ids"] == call["ids"], result["question_id"]
    assert isinstance(result["recognized_missing_evidence"], bool), result["question_id"]
assert not any(searches.values()), "Unmatched recorded searches"
(OUT / "results.json").write_text(json.dumps(declared, indent=2) + "\n")
logger.info(
    f"Verified {executed['bm_search']} actual text searches, {executed['bm_read']} reads, returned ID order, "
    f"provenance, and unchanged corpus. Wrote {OUT / 'results.json'}."
)
