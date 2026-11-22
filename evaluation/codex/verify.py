import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
events = [json.loads(line)["message"] for line in (OUT / "events.jsonl").read_text().splitlines()]
assert any(e.get("method") == "turn/completed" and e["params"]["turn"]["status"] == "completed" for e in events)
items = [e["params"]["item"] for e in events if e.get("method") == "item/completed"]
calls = [item for item in items if item["type"] == "mcpToolCall"]
assert not any(
    item["type"] in {"commandExecution", "fileChange", "webSearch", "dynamicToolCall", "collabAgentToolCall"}
    for item in items
)
assert all(
    c["server"] == "basic_memory"
    and c["tool"] in {"bm_search", "bm_read"}
    and c["status"] == "completed"
    and c["error"] is None
    for c in calls
)
inventory = json.loads((OUT / "effective-tools.json").read_text())
assert inventory.get("nextCursor") is None
assert {t["name"] for s in inventory["data"] for t in s["tools"].values()} == {
    "bm_search",
    "bm_read",
}
assert all(s.get("runtimeStatus") == "connected" and not s.get("toolsError") for s in inventory["data"])

notes = {}
source_revision = (
    "sha256:" + hashlib.sha256((ROOT / "evaluation/harness-independent-shared-memory.md").read_bytes()).hexdigest()
)
for path in (ROOT / "evaluation/corpus").glob("*.md"):
    metadata = dict(
        (key, json.loads(value))
        for key, value in (line.split(": ", 1) for line in path.read_text().split("---\n", 2)[1].splitlines())
    )
    assert metadata["review_status"] == "accepted" and metadata["source_revision"] == source_revision
    notes[metadata["permalink"]] = metadata["id"]
assert len(notes) == 20
searches = defaultdict(deque)
for call in calls:
    structured = call["result"]["structuredContent"]
    result = structured.get("result", structured)
    assert not call["result"].get("isError")
    if call["tool"] == "bm_search":
        assert call["arguments"]["mode"] == "text"
        searches[call["arguments"]["query"]].append((call, [notes[row["permalink"]] for row in result["results"]]))
    else:
        assert result["frontmatter"]["id"] == notes[result["permalink"]]
        assert result["frontmatter"]["source_revision"] == source_revision
assert sum(map(len, searches.values())) == 22

response = (OUT / "client-response.txt").read_text().strip()
if response.startswith("```json\n") and response.endswith("\n```"):
    response = response[8:-4]
results = json.loads(response)
questions = json.loads((ROOT / "evaluation/questions.json").read_text())
assert [r["question_id"] for r in results] == [q["id"] for q in questions]
for result in results:
    call, actual_ids = searches[result["query"]].popleft()
    assert result["mode"] == call["arguments"]["mode"]
    assert result["retrieved_ids"] == actual_ids, result["question_id"]
    assert isinstance(result["recognized_missing_evidence"], bool)
assert not any(searches.values())
assert json.loads((OUT / "corpus-before.json").read_text()) == json.loads((OUT / "corpus-after.json").read_text())
(OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
(OUT / "tool-calls.json").write_text(json.dumps(calls, indent=2) + "\n")
logger.info(
    f"Verified 22 actual text searches, {len(calls) - 22} reads, returned ID order, provenance, and unchanged corpus. "
    f"Wrote {OUT / 'results.json'}."
)
