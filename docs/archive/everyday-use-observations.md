# Historical everyday-use observation log

This log retains the earlier read-only trial plan and its recorded preparation. Its manual reporting requirements and numerical adoption gate are superseded by the [scope reconciliation](scope-reconciliation.md) and [automatic lightweight observation decision](../adr/0012-automatic-lightweight-handover-observations.md). New productive observations belong in the external local log during setup, not in this historical template.

**Closed as historical on 18 November 2026.** No qualifying session was recorded
under these manual rules, and none is now required. [ADR 0011](../adr/0011-real-project-use-with-ongoing-evaluation.md)
replaced the numerical gate with ongoing observation review, and
[ADR 0012](../adr/0012-automatic-lightweight-handover-observations.md)
moved recording to the external JSONL log during real work (see
[automatic observations](automatic-observations.md)). The remaining
roadmap item is the [review of real observations](ROADMAP.md), not a rerun of
this template.

## During normal work

Use the existing clients and global search/read access with ordinary coding
tools retained. Do not use the restricted evaluation agents or inject recording
hooks. Start with actual work, not a benchmark question or a reminder to search
memory. Record whether startup recall happened before any reminder. If useful,
explicitly request retrieval later; record that separately, without relabelling
it as startup recall.

Use this checkout and a separate existing work repository as the
initial repository pair **when there is real work there**; substitute another
actual repository if needed. These are work locations, not two new memory
stores. Scope searches to the appropriate existing memory project; global
access does not make this corpus applicable to every repository. Keep the
single owner-maintained corpus and existing configuration.

After each session, copy the session block below and add one opportunity block
per distinct recall-relevant task/decision, including failures and occasions
when no retrieval occurred. A session counts once regardless of its number of
turns, searches or clients. Do not split a task into sessions to reach the gate.
Sessions with no recall opportunity can be recorded but do not count.

Link the client's existing transcript/export or retained raw events under
`evaluation/phase1a/runs/`; do not copy secrets or full private transcripts into
this tracked log. Record actual search arguments and read identifiers, returned
IDs (including irrelevant results), the note's stable ID/revision/source, and
the decision it supported. Search snippets alone are not a source inspection.
Use explicit `mode: "text"` for deliberate searches under the historical embedding
exception; record omitted modes honestly rather than rewriting the call.

Record per-call latency from paired call/result timestamps, matched by call ID
or exact arguments, not completion order. Include unsuccessful calls and
timeouts. Distinguish tool round-trip time from full client-turn/startup time;
neither isolates model reasoning. If timestamps are unavailable, mark latency
unknown, not zero, and retain that evidence gap for closure. Also record whether
the user abandoned retrieval because of latency.

Compare useful recall with the investigation that would otherwise have been
needed in repository docs/code/history. Name the avoided steps and estimate
their saved minutes with a basis and owner confirmation; do not count reading
time twice or claim savings merely because a note was returned. Record actual
maintenance minutes (corpus review, corrections, configuration, indexing,
recording), with preparation separated from recurring work. Unknown costs and
savings remain unknown; they cannot support a passing cost comparison.

If memory is unavailable, state that visibly, continue using repository
sources, and record the fallback. Do not create a second authoritative store.
Provisioning, reviewer actions, reindexing and service control stay in the
owner's terminal. A naturally occurring outage is useful evidence; do not stop
the live service to manufacture one.

## Unchanged decision rule

From [architecture section 13](../../evaluation/harness-independent-shared-memory.md#13-acceptance-criteria-and-rollout-gates):

> Global retrieval access is exercised during normal work until the minimum observation is reached: at least 10 recall-relevant work sessions across at least 2 repositories over at least 7 days. Success requires at least 3 documented useful recalls (task, query, note used, avoided investigation, estimated saving), at most 2 missed recalls of accepted content that should have surfaced, fewer false recalls than useful recalls, no retrieval abandoned because of latency (latency recorded per retrieval), and maintenance effort below the documented saved investigation time; discovered wrong accepted entries are corrected or captured as proposals before the evaluation closes. After 10 recall opportunities without a single useful recall, the trial may be judged failed early.

Keep UTC session start/end times so the observation span is auditable. Do not
close merely because seven calendar dates or ten tool calls have accumulated.
The early-failure option is based on opportunities, not sessions, and is not an
automatic failure or permission to lower the success criteria.

Classify opportunities as:

- **Ordinary startup:** real work; retrieval initiated before an explicit memory
  reminder, with normal tools/settings. Include the original task prompt.
- **Explicitly prompted:** real work with a memory reminder or requested query.
  It may demonstrate practical value, but not unprompted startup. Report its
  outcomes separately as well as in real-work totals.
- **Synthetic/preparation:** fixed questions, staged startup/outage checks,
  inventory checks and this evaluation setup. Exclude from everyday sessions,
  opportunities, useful/missed/false recalls, savings and observation span.
  Keep preparation effort visible in the maintenance ledger.

Useful means the retrieved accepted content actually helped the task. A miss
needs an identified accepted, applicable note that should have surfaced and a
reason it was expected; log both failure to search and unsuccessful searches.
A false recall is incorrect/inapplicable memory presented or used as applicable
guidance, not simply an irrelevant hit in a result list. Record mixed outcomes
explicitly instead of hiding their incorrect parts. A justified no-answer is
not automatically a miss.

## Session template

```text
Session ID:
UTC start / end:
Repository (path/remote), branch / commit:
Client / version / model; existing session or transcript reference:
Actual task / original first prompt:
Global memory connection / effective search-read inventory evidence:
Ordinary coding tools retained? Configuration overrides, if any:
Recall-relevant? Qualifies as real work? Reason if excluded:
Startup recall before reminder: yes / no / unknown (evidence):
Opportunity IDs:
Maintenance IDs:
```

```text
Opportunity ID / session ID / UTC:
Class: ordinary-startup / explicitly-prompted / synthetic-preparation
Task or decision / why accepted memory was relevant:
Reminder wording and time, if any:
Actual search arguments (project, query, mode, filters, etc.):
Returned IDs in order / irrelevant hits / actual read arguments:
Note used or expected: stable ID, accepted revision/checksum, source URI/revision:
Source inspected / applicability checked against current checkout:
Outcome: useful / missed / false / justified-no-answer / no-benefit / unresolved
What changed in the work because of recall (or what went wrong):
Avoided investigation (specific normal docs/code/history steps):
Estimated saved minutes / estimation basis / owner confirmation:
Each retrieval: call ID, tool, start/end, latency ms, success/error; raw evidence:
Startup/whole-turn seconds separately, if available:
Retrieval abandoned because of latency: yes / no / unknown:
Outage notice / continued coding / fallback store, if relevant:
Maintenance minutes and ledger ID:
Wrong accepted entry / correction ID and disposition, if discovered:
```

## Real-work observations

None recorded yet. Do not backfill historical synthetic runs as work sessions.

## Maintenance ledger

| ID | UTC/date | Work | Active minutes | Evidence / owner confirmation |
| --- | --- | --- | --- | --- |
| M001 | 2026-11-17 | Trial preparation, evidence reconciliation, log setup and synthetic checks | Unknown; owner to record, not inferred from process runtime | This change and P001–P003 below; keep separate from recurring maintenance |

Add actual maintenance entries as incurred, including recording time and
correction effort. At closure report preparation, recurring and total minutes
against documented real-work savings; do not silently omit preparation.

## Preparation / synthetic evidence (excluded)

| ID | Date | Task, retrieval and outcome | Savings / latency |
| --- | --- | --- | --- |
| P001 | 2026-11-17 | Explicit preparation request. OpenCode searched all projects in text mode for `"Phase 1A" OR "everyday" OR "startup"`; read `main/memory-12.md`, `main/memory-18.md`, `main/memory-19.md` through `bm_read`. Accepted IDs `memory-12`, `memory-18`, `memory-19`, source revision `sha256:109ea610ebdaef9153f888a8aa76be1b45f42bd57061629ee1aafb8ca17f62aa`. Compared with current architecture sections 8/13 and recorded reports; C001 captures the stale single-work-repository interpretation. No startup claim or avoided investigation established. | Savings not claimed; tool latency unavailable in this transcript. Not a qualifying session/opportunity. |
| P002 | 2026-11-17 06:24:17–06:24:21 UTC | Claude Code 2.1.311, normal discovery in the second work repository, default `claude-opus-5-5`, no startup-wait/model/tool/MCP/settings override and no injected hook. Reused the existing SQLite/two-laptop startup prompt, adding advice-only/no-file-change wording. Init retained ordinary tools but Basic Memory was `pending` with no memory tools; provider returned HTTP 402 before any tool call. Exit 1; no completed advice/recall. Connection outcome and first-turn recall remain unproven, not failed on the basis of `pending`. | Whole invocation 3.664119 s; no retrieval latency or saving. [Invocation](../../evaluation/phase1a/runs/20261117-preparation/invocation.json), [raw events](../../evaluation/phase1a/runs/20261117-preparation/events.jsonl), [timestamped events](../../evaluation/phase1a/runs/20261117-preparation/timed-events.jsonl), [exit](../../evaluation/phase1a/runs/20261117-preparation/run-exit.json). |
| P003 | 2026-11-17 06:31:33–06:31:35 UTC | Codex 0.169.0, global configuration discovered in the second work repository; ephemeral read-only thread with approvals disabled, no model turn or injected instructions/configuration. `mcpServerStatus/list` reported `connected` and exactly `bm_read`, `bm_search`. Retained the previously unarchived kind of global live-inventory evidence, not startup recall. | No retrieval or saving. [Invocation](../../evaluation/phase1a/runs/20261117-preparation/codex-invocation.json), [raw timestamped protocol](../../evaluation/phase1a/runs/20261117-preparation/codex-events.jsonl), [live inventory/version](../../evaluation/phase1a/runs/20261117-preparation/codex-inventory.json). |

P002 was not retried with another model or funded account. Its 180-second
technical timeout was not reached and is not a new acceptance threshold.
[Preservation manifests](../../evaluation/phase1a/runs/20261117-preparation/preservation.json) confirm all
27 corpus Markdown files and 13,358 pre-existing evidence files unchanged.
Raw runs are ignored local artifacts; the recorded findings here survive a
fresh clone.

## Correction proposals

### C001 — `memory-18`: distinguish corpus location from work repositories

Discovered during P001; applied on 18 November 2026 as part of the
[source-revision reconciliation](source-provenance.md), after the
architecture source itself was clarified. The retained proposal below records
what P001 observed; the applied wording follows the revised source.

The accepted note's historical “one repository” wording could mislead the current
multi-repository practical trial. Its original section-8 source was historical
guidance, not evidence that section 13's later two-repository gate is satisfied.

Proposed replacement for that sentence: “The early trial uses one owner-maintained
curated corpus, one owner and one writer host, with 20–30 reviewed,
non-sensitive records carrying sources and stable IDs. Exercise global
read-only recall during real work across at least two repositories under the
everyday-use gate in architecture section 13.”

Source: architecture sections 8/13 and the approved 15 November phase-plan
change in `docs/evaluation-results.md`. Preserve the stable note ID and existing
safety guidance; the owner must review and update source provenance at acceptance.
No native write, reviewer operation or reindex was performed. Add other wrong
accepted entries here (or link an explicit owner correction) before closure.

## Closure worksheet

Still pending: qualifying sessions **0**, repositories exercised in qualifying
sessions **0**, first/last qualifying UTC dates and observation span **not yet
established**. No real-work recall outcomes, savings, latency-abandonment result
or maintenance comparison have been measured. The absence of observations is
not zero demonstrated misses/false recalls or a pass.

At closure list qualifying session/opportunity IDs; totals and separate
startup/prompted outcomes; useful/missed/false recall evidence; all retrieval
latencies and abandonments; saved investigation minutes versus maintenance;
and every correction's applied/proposed disposition. Apply the unchanged rule
above, including its early-failure option, and record pending/pass/fail with the
supporting evidence. Then assess remaining inherited gates and seek rollout approval
separately; this log never enables capture.
