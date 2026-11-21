import hashlib
import json
import re
import statistics
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.opencode.inventory import ALLOWED_TOOLS, verify_inventory  # noqa: E402

OUT = Path(sys.argv[1]).resolve()


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# Raw client event stream captured by the runner (`opencode run --format json`).
events = []
for line in (OUT / "client-response.txt").read_text().splitlines():
    if line.strip():
        events.append(json.loads(line))
assert events, "No client events"
assert not any(e.get("type") == "error" for e in events), "Client stream contains error events"
text_parts = [e["part"]["text"] for e in events if e.get("type") == "text"]
assert text_parts, "Client produced no text"
session_id = events[0]["sessionID"]
assert all(e["sessionID"] == session_id for e in events)

# Raw tool calls captured by the project-local evaluation plugin.
plugin_events = [
    json.loads(line)
    for line in (ROOT / "evaluation/opencode/runs" / session_id / "events.jsonl").read_text().splitlines()
]
snapshot = verify_inventory(plugin_events)
inventory = set(snapshot["tools"])

versions = json.loads((OUT / "client-version.json").read_text())
assert versions["basic_memory"].startswith("Basic Memory version:"), versions

# Actual executions: raw arguments, results, and latency from the hooks.
befores = {e["callID"]: e for e in plugin_events if e["kind"] == "tool.execute.before"}
afters = {e["callID"]: e for e in plugin_events if e["kind"] == "tool.execute.completed"}
errors = [e for e in plugin_events if e["kind"] == "tool.execute.error"]
assert not errors, f"Tool errors: {errors}"
assert set(befores) == set(afters), "Unpaired tool executions"
calls: list[dict[str, Any]] = []
for key, after in afters.items():
    before = befores[key]
    assert before["tool"] == after["tool"], "Tool mismatch between hooks"
    assert after["tool"] in ALLOWED_TOOLS, f"Executed tool outside allowlist: {after['tool']}"
    output = after["result"]["output"]
    if after["tool"] == "basic_memory_bm_search":
        results = output.get("result", output).get("results", [])
        rows = [{"permalink": row["permalink"], "entity": row.get("entity")} for row in results]
    else:
        rows = output
    calls.append(
        {
            "id": key,
            "tool": after["tool"],
            "arguments": before["input"],
            "result": after["result"],
            "rows": rows,
            "started": before["time"],
            "ended": after["time"],
            "latency_ms": (parse_time(after["time"]) - parse_time(before["time"])).total_seconds() * 1000,
        }
    )

searches = defaultdict(deque)
for call in calls:
    if call["tool"] == "basic_memory_bm_search":
        assert call["arguments"].get("mode") == "text", call["arguments"]
        searches[call["arguments"]["query"]].append(call)
assert len(calls) >= len(searches), "Inconsistent call accounting"
latencies = [call["latency_ms"] for call in calls if call["tool"] == "basic_memory_bm_search"]

# Corpus provenance: stable IDs and accepted source revisions.
notes = {}
source_revision = (
    "sha256:" + hashlib.sha256((ROOT / "evaluation/harness-independent-shared-memory.md").read_bytes()).hexdigest()
)
for path in (ROOT / "evaluation/corpus").glob("*.md"):
    metadata = dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in path.read_text().split("---\n", 2)[1].splitlines())
    )
    assert metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision, path
    notes[metadata["permalink"]] = metadata["id"]
assert len(notes) == 20

returned_ids = set()
read_ids = set()
for call in calls:
    if call["tool"] == "basic_memory_bm_search":
        for row in call["rows"]:
            assert row["permalink"] in notes, f"Unknown permalink returned: {row['permalink']}"
        call["ids"] = [notes[row["permalink"]] for row in call["rows"]]
        returned_ids.update(call["ids"])
    else:
        frontmatter = dict(
            (key, json.loads(value))
            for key, value in (line.split(": ", 1) for line in call["rows"].split("---\n", 2)[1].splitlines())
        )
        assert frontmatter["id"] == notes[frontmatter["permalink"]], call["rows"][:200]
        assert frontmatter["source_revision"] == source_revision, call["rows"][:200]
        read_ids.add(frontmatter["id"])

# The client's declared results, checked against the actual calls.
response = text_parts[-1].strip()
if response.startswith("```"):
    response = re.sub(r"^```[a-z]*\n", "", response)
    response = re.sub(r"\n```$", "", response)
results = json.loads(response)
questions = json.loads((ROOT / "evaluation/questions.json").read_text())
assert [r["question_id"] for r in results] == [q["id"] for q in questions], "Question order mismatch"
for result in results:
    assert result["query"] in searches, f"No recorded search for query: {result['query']!r}"
    call = searches[result["query"]].popleft()
    assert result["mode"] == call["arguments"].get("mode"), result["question_id"]
    assert result["retrieved_ids"] == call["ids"], result["question_id"]
    assert isinstance(result["recognized_missing_evidence"], bool), result["question_id"]
assert not any(searches.values()), "Unmatched recorded searches"
assert json.loads((OUT / "corpus-before.json").read_text()) == json.loads((OUT / "corpus-after.json").read_text()), (
    "Corpus bytes changed"
)
(OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
(OUT / "tool-calls.json").write_text(json.dumps(calls, indent=2) + "\n")
(ROOT / "evaluation/results-opencode.json").write_text(json.dumps(results, indent=2) + "\n")
summary = {
    "returned_permalinks_verified": True,
    "local_corpus_source_revision_verified": True,
    "read_ids_with_verified_source_revision": sorted(read_ids),
    "returned_ids_without_verified_source_revision": sorted(returned_ids - read_ids),
    "served_source_revisions_verified": bool(returned_ids) and returned_ids <= read_ids,
}
(OUT / "verification-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
logger.info(
    f"Verified {len(latencies)} actual text-mode searches, {len(calls) - len(latencies)} reads, "
    f"effective inventory {sorted(inventory)}, returned ID order, local corpus provenance, and unchanged corpus. "
    f"Served source revisions verified: {summary['served_source_revisions_verified']}. "
    f"Search latency {min(latencies):.0f}-{max(latencies):.0f} ms, median {statistics.median(latencies):.0f} ms. "
    f"Wrote results-opencode.json."
)
