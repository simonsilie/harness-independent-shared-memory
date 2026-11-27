# Automatic lightweight observations

Activated in the common dotfiles AGENTS file for Codex and OpenCode on
18 November 2026 after explicit owner approval. The productive log is outside
repositories. These instructions implement [ADR 0012](adr/0012-automatic-lightweight-handover-observations.md)
using existing Python and filesystem tools; no installed writer or hook is needed.

## Shared client instructions

- Automatically append an observation when real work offers evidence about a
  temporary handover: capture, attempted resumption, continuation, a missed
  handover, or an owner reminder/correction. Do this before ending the relevant
  turn, without asking for individual observation approval. Do not manufacture
  opportunities or treat an empty startup search as a missed handover.
- Write to `$HOME/SharedMemory/observations/observations.jsonl`, outside the
  repositories and indexed note roots. This is observation metadata, separate
  from knowledge entries and temporary notes. Do not save it through `bm_write`,
  copy transcripts or secrets, or promote handover content into durable memory.
- Each line is one JSON object with exactly these fields: `timestamp` (current
  UTC ISO 8601), `project`, `handover_id`, `from_client`, `to_client`,
  `found_without_reminder` (`yes`, `no`, `unknown`), `continuation` (`successful`,
  `partial`, `failed`, `unrated`), `problem_or_assistance`, `session_reference`,
  and `owner_feedback`. Use native handover identifiers and an existing continuing
  session reference when available. Unavailable identifiers, clients, project,
  assistance, session references and feedback are JSON `null`, never invented.
- Set `found_without_reminder=yes` when this session retrieved the handover
  before an explicit owner reminder to consult memory. An ordinary request to
  continue a topic is not such a reminder. Set `no` when retrieval needed that
  reminder or there is evidence of a missed handover. Use `unknown` only when
  the ordering/evidence is unavailable, including capture without resumption.
  Later reminders do not change an already observed unprompted discovery.
  Retrieval alone is not successful continuation.
  Assess actual work: `successful` needs evidence that the pending work resumed;
  `partial` means only some resumed; `failed` means an observed failed attempt;
  use `unrated` for capture alone or when the outcome is unavailable.
- `continuation` and `problem_or_assistance` are agent assessments. Put owner
  feedback only in `owner_feedback`, using the owner's actual feedback, otherwise
  `null`. Later evidence or feedback is a new observation, referencing the same
  handover and session where known; never rewrite earlier lines.
- Use the append recipe below with existing Python and pass one JSON object on
  standard input. Every writer must lock the log itself and flush before closing
  it. Do not replace the file or perform a read/modify/write cycle. Keep existing
  permissions private. The productive directory/log already exist; do not create
  a fallback store or change client/system configuration if access is denied.
- If recording fails or tools cannot access the external path, report the failure
  briefly and continue independent work. A permission error is not approval to
  bypass a sandbox. Do not claim that an observation was saved without a
  successful write. This is a client workflow convention, not a server guarantee.

## Append recipe

Run this Python code with the existing interpreter (for example as the code
argument to `python3 -c`), supplying the observation JSON on standard input.
The lock covers the complete encoded record, including embedded newlines and
non-ASCII text; closing the stream releases it, including on process failure.
All participating sessions must use this protocol. It prevents concurrent
interleaving, not disk failure or a process being killed midway through a write.

```python
import fcntl
import json
import os
import sys
from pathlib import Path

record = json.load(sys.stdin)
payload = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
path = Path.home() / "SharedMemory/observations/observations.jsonl"
os.umask(0o077)
with path.open("ab") as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    stream.write(payload)
    stream.flush()
```
