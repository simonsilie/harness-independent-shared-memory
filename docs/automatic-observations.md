# Lightweight automatic observations

The [shared client addition](shared-memory-observations.md) is activated for
Codex and OpenCode after explicit owner approval on 18 November 2026, using the external log already reserved at
`$HOME/SharedMemory/observations/observations.jsonl`. It implements
[ADR 0012](adr/0012-automatic-lightweight-handover-observations.md) with existing
Python standard-library tools and a shared template. No custom writer, software
installation, dashboard or transcript capture is needed.

## Active behavior

Agents record capture, attempted resumption, continuation, demonstrated misses,
reminders and corrections during real work without requiring a manual report.
Retrieval alone does not establish continuation; unavailable outcomes remain
`unrated`, unknown reminder status remains `unknown`, and unavailable identifiers
remain `null`. Agent assessments and optional owner feedback have separate
fields. Follow-up evidence appends another observation rather than changing
history. Recording failures remain visible without blocking independent work.

All writers acquire an exclusive advisory lock on the same log, append one
encoded JSON line, flush, and close the file before releasing the lock. This
covers records larger than a single filesystem write and preserves embedded
newlines and Unicode. Existing bytes are never rewritten. The protocol requires
cooperating writers and does not promise recovery from a killed writer or disk
failure. The log stays outside Basic Memory's indexed note roots.

## Verification on 18 November 2026

The exact Python recipe from the candidate instructions was executed against a
disposable log inside this checkout, changing only its destination path.
Twelve independent Python processes each appended 32 observations concurrently,
including 64 KiB assistance fields, Unicode, quotes, escaped newlines, all reminder
and continuation values, unknown identifiers and optional synthetic feedback.
All 384 records were read back and compared with their input objects. No records
were lost, duplicated or corrupted; each session's append order, pre-existing
log bytes and mode `0600` were preserved. Synthetic feedback and observations
exist only in the disposable check, not in productive memory.

Evidence and the repeatable probe are retained under
`.state/observation-setup/`: `verify.py`,
`20261118T060104.875814Z/result.json` and that run's disposable JSONL log.
The extracted recipe SHA-256 is
`da643f45b993a31258087ea1d1d99edecab09bf16cfeff5dd60f4652a1c1b4c7`.
Reproduce without installing anything:

```sh
uv run --locked --no-sync python .state/observation-setup/verify.py
```

This establishes concurrent append behavior, not that either client will
consistently recognize observation opportunities or execute the recipe.

## Activation on 18 November 2026

Activation added the shared rules to the Toolbox instructions. Both clients
load the same file through their instruction symlinks. Staged copies, manifests
and read-back evidence stay local.

## Actual client verification

The probe at `.state/observation-setup/verify-clients.py` reuses the existing
client runners with Codex in workspace-write mode. It supplies no candidate
instruction override; the only prompt-level routing change sends synthetic
observations to a disposable project-local log. Native MCP operations use
disposable model-free stores, while client session state uses normal locations.

The first Codex run, `evaluation/clients/runs/20261118T060454.266760Z/`,
automatically recorded capture as `unrated`, actual continuation as `partial`,
and the subsequent completion as `successful`, including separate owner
feedback. It conservatively marked unprompted discovery as `unknown` even
though the trace established retrieval before any reminder. The shared rule
was clarified to assess this session's ordering explicitly, distinguish an
ordinary continuation request from a memory reminder, and preserve an already
observed unprompted discovery when a later reminder arrives. The first run is
retained as evidence and is not counted as a passing verification.

The clarification was applied and read back in the same common file;
`.state/observation-setup/clarification.json` records its final SHA-256.
Both installed clients passed the repeat with their globally loaded rules,
without an instruction override:

- Codex: `evaluation/clients/runs/20261118T060739.418074Z/`.
- OpenCode: `evaluation/clients/runs/20261118T060739.116757Z/`.

Each client captured a handover without reading the result files and recorded
`unknown`/`unrated`. In a fresh session, ordinary scoped recall retrieved the
handover, the client read only result A, and recorded `yes`/`partial`.
A subsequent reminder triggered reading result B and recorded `yes`/`successful`
with the exact owner feedback in its separate field. Unpredictable file contents
were checked against the answers; all JSON fields and private permissions were
inspected. No prompt asked either client to record an observation, and neither
requested per-record approval. Each run's `result.json` confirms that productive
notes, the historical corpus and the productive observation log were unchanged.

These are synthetic workflow checks, separate from real-project observations;
they do not establish everyday usefulness or guarantee future agent compliance.
The append concurrency check separately covers `no`/`failed` values and large
records; the real-client check does not manufacture a failed continuation.

## Productive observations

The [observation review](observation-review.md) records the findings from
ordinary use. Detailed observation records stay in the local log.
