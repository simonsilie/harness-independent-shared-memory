import json
import re
import sys
from collections import Counter
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.opencode.inventory import ALLOWED_TOOLS, verify_inventory  # noqa: E402
from evaluation.support import sha256_file  # noqa: E402

OUT = Path(sys.argv[1]).resolve()

events = []
for line in (OUT / "client-response.txt").read_text().splitlines():
    if line.strip():
        events.append(json.loads(line))
assert not any(e.get("type") == "error" for e in events), "Client stream contains error events"
assert events, "No client events"
session_id = events[0]["sessionID"]
assert all(e["sessionID"] == session_id for e in events), "Mixed client sessions"
texts = [e["part"]["text"] for e in events if e.get("type") == "text"]
assert texts, "Client produced no text"

plugin_events = [
    json.loads(line)
    for line in (ROOT / "evaluation/opencode/runs" / session_id / "events.jsonl").read_text().splitlines()
]
snapshot = verify_inventory(plugin_events)
assert not any(term in snapshot["system"][0].lower() for term in ("memory", "recall", "search")), (
    "Agent instructions mention memory retrieval"
)
assert not any(e["kind"] == "tool.execute.error" for e in plugin_events), "Tool errors occurred"
assert all(e["tool"] in ALLOWED_TOOLS for e in plugin_events if e["kind"].startswith("tool.execute.")), (
    "Tool outside allowlist"
)
executed = Counter(e["tool"] for e in plugin_events if e["kind"] == "tool.execute.completed")
assert executed["basic_memory_bm_search"] > 0, "No startup search executed"
assert executed["basic_memory_bm_read"] > 0, "No startup read executed"
befores = {e["callID"]: e for e in plugin_events if e["kind"] == "tool.execute.before"}
afters = {e["callID"]: e for e in plugin_events if e["kind"] == "tool.execute.completed"}
assert set(befores) == set(afters), "Unpaired tool executions"
relevant_search = False
relevant_read = False
source_revision = "sha256:" + sha256_file(ROOT / "evaluation/harness-independent-shared-memory.md")
for key, call in afters.items():
    assert befores[key]["tool"] == call["tool"], "Mismatched tool execution"
    output = call["result"]["output"]
    if call["tool"] == "basic_memory_bm_search":
        result = output.get("result", output)
        if isinstance(result, str):
            relevant_search |= bool(re.search(r"^- memory-20\.md \|", result, re.MULTILINE))
        else:
            relevant_search |= any(row["permalink"] == "memory-20" for row in result["results"])
    else:
        frontmatter = dict(
            (key, json.loads(value))
            for key, value in (line.split(": ", 1) for line in output.split("---\n", 2)[1].splitlines())
        )
        if frontmatter["id"] == "memory-20":
            assert frontmatter["source_revision"] == source_revision, "Stale SQLite guidance"
            assert frontmatter["review_status"] == "accepted", "Unaccepted SQLite guidance"
            relevant_read = True
assert relevant_search and relevant_read, "Startup did not retrieve and read the SQLite guidance"
assert json.loads((OUT / "corpus-before.json").read_text()) == json.loads((OUT / "corpus-after.json").read_text()), (
    "Corpus bytes changed"
)
prompt = (OUT / "prompt.txt").read_text()
assert "memory" not in prompt.lower() and "search" not in prompt.lower(), "Prompt mentions memory retrieval"
result = {
    "session_id": session_id,
    "prompt": prompt,
    "prompt_mentions_retrieval": False,
    "effective_tools": sorted(snapshot["tools"]),
    "executed_tools": dict(executed),
    "searches": sum(v for k, v in executed.items() if k == "basic_memory_bm_search"),
    "reads": sum(v for k, v in executed.items() if k == "basic_memory_bm_read"),
    "client_response": texts[-1],
}
(OUT / "startup-result.json").write_text(json.dumps(result, indent=2) + "\n")
logger.info(
    f"Startup check verified: {result['searches']} searches, {result['reads']} reads, "
    f"inventory {result['effective_tools']}, corpus unchanged. Wrote startup-result.json."
)
