# Recorded evaluation results

The [scope reconciliation](scope-reconciliation.md) supersedes the former rollout requirements referenced below. Recorded observations remain evidence of what was tested, not a pass or failure against the revised scope. Live client configuration has not been changed by the documentation update.

## Current status — 18 November 2026

**Productive use is configured; all roadmap items are complete, including the review of observations from real projects. The [custom-code decision](custom-code-decision.md) archives all `workflow/` modules and their historical-only probes/tests at tag `historical-workflow-20261118`.** The external store, both client connections, temporary context, automatic observations, backup/restore and portable export are verified ([roadmap](ROADMAP.md)). The former everyday-use gate and rollout approval no longer govern adoption; [ADR 0011](adr/0011-real-project-use-with-ongoing-evaluation.md) and the [scope reconciliation](scope-reconciliation.md) replace them with ongoing observation review. The sections below remain historical evidence.

Historical source links below are pinned to the
[complete archived tree](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61).
Commands referring to `workflow/` or `evaluation/workflow/` require that checkout;
see [historical reproduction](custom-code-decision.md#historical-reproduction).
Raw evidence stays at its original ignored paths. Active native probe commands
now use `evaluation/native/` as documented in the [repository architecture](repository-architecture.md).

The dated sections below preserve what each run established **at that time**.
Their outstanding-work statements are historical, not a current aggregate
status. In particular, E13's protected real-client workflow was followed by
E14's repeated-read/rebuilt-index/restart eligibility, E15's time-only expiry,
E16's protected logical/SQLite normal restores, and E18's protected races and
bounded overlapping three-client load. E17's argument-fidelity failure remains
failed; E18 is a separate fresh run, not a repaired historical pass. These are
isolated deployment results, not ordinary access or rollout authorization.

The table below records the former everyday-use criteria as historical. ADR 0011 no longer requires them; keep it for its evidence links, not as a current checklist.

| Inherited early-trial evidence | Observed evidence | Remaining ordinary-use evidence |
| --- | --- | --- |
| Cross-client quality and provenance | Fixed 20-question scores: Codex 19, OpenCode 20, Claude 19 hits at five; all recognize both no-answer questions. Engine-served identity/source verification passed. | Do not substitute those scores for practical value or current source/applicability checks. |
| Global read-only access | Existing global checks in a second work repository: OpenCode connected with ordinary tools; Claude connected only after a temporary startup-wait override. New P003 archives Codex 0.169.0's global live inventory: connected, exactly `bm_read`/`bm_search`, no model turn. | Retain effective search/read-only inventories and client versions in actual work. P003 used an ephemeral read-only thread with approvals disabled; it does not establish ordinary first-turn recall. These are point-in-time workflow restrictions, not an OS boundary. No global settings changed for this preparation. |
| Startup recall | All three previously recalled without a reminder in restricted synthetic sessions. | Normal-checkout first-turn recall/reliability in each client remains open. Distinguish spontaneous startup, later explicitly requested real-work retrieval, and synthetic probes. |
| Claude normal first turn | New P002: normal settings/tools/global registration in the second checkout, no wait override or injected hook. Init was `pending`; HTTP 402 stopped the turn before any tool call after 3.664119 seconds. | Neither failure-to-connect nor successful first-turn retrieval is established. Existing default model credits block this attempt; no model/funding change or automatic retry was made. |
| Startup outage | Codex visibly blocks required-server startup. OpenCode exposes failed status, but its synthetic model response did not recognize missing evidence adequately. Claude's prior hook-blocked inventory showed failed status only. | Claude's model-level outage notice/continuation remains unobserved; OpenCode's ordinary operator/model notice needs evidence. Client status alone does not prove useful degraded-task behavior. |
| Mid-task outage | E16 retains four transport failures from an accidental protected-facade stop, then a retry-only harness continuation. | This is not an ordinary native-memory coding session demonstrating visible notice, continued work and no fork. Observe a natural outage or arrange a separate owner-controlled disposable test; never stop the live service for this trial. |
| Recovery and cost | Original curated-document restore/index rebuild passed; E16 separately covers supported workflow normal restore. Initial download and isolated indexing cost are recorded. | Original recovery glob excludes later `evaluation/corpus/pilot/` notes. Expanded-corpus restore, in-use background indexing cost and maintenance versus saved investigation remain unmeasured. Any new restore/reindex stays in the owner's terminal. |
| Everyday value and corrections | Log opened; preparation P001–P003 excluded. C001 captures a proposed clarification of accepted `memory-18`'s single-repository wording, without altering the corpus. | At least 10 relevant work sessions, 2 repositories, 7 days and all unchanged value/error/latency/effort/correction criteria must be observed before closure. |

P002 reuses the existing Claude startup prompt and stream-JSON recording format,
with normal discovery and advice-only/no-file-change wording. Its
[raw events](../evaluation/phase1a/runs/20261117-preparation/events.jsonl),
[invocation](../evaluation/phase1a/runs/20261117-preparation/invocation.json),
[UTC/timing/exit](../evaluation/phase1a/runs/20261117-preparation/run-exit.json)
and [preservation manifest](../evaluation/phase1a/runs/20261117-preparation/preservation.json)
are retained locally. All **27 live-corpus files and 13,358 pre-existing evidence
files** matched before/after; no memory mutation tool was called. The pending
inventory is not a verified tool allowlist. Process time is not retrieval
latency or human maintenance effort. Preparation effort is explicitly unknown
in the ledger, not a fabricated zero or saving.

P003 closes the absence of an archived Codex global live inventory, not the
ordinary-startup gap. It reuses the existing app-server recording protocol with
normal global/project discovery in a second work repository, an ephemeral
read-only thread and approvals disabled, without a model turn or tool call.
The [live version/inventory](../evaluation/phase1a/runs/20261117-preparation/codex-inventory.json)
and [timestamped protocol](../evaluation/phase1a/runs/20261117-preparation/codex-events.jsonl)
retain the connected status and exact two-tool surface.

For normal work, append a session and its opportunity blocks to the log using
the existing client transcript, then record actual per-call latency, task/query/
note, outcome, avoided investigation, estimated saving, maintenance and
corrections. No recorder daemon, new client, automatic hook or deployment is
needed. Owner-terminal provisioning, review, reindexing and service control are
not needed to begin observations; no such operations were run.

The [capability inventory](historical-capability-inventory.md) separates the later protected
test evidence from current rollout gaps: inherited ordinary-use evidence,
deployment-wide model independence, active-cache behavior where applicable,
and an explicit deployment/rollout decision. Persistent deployment, sustained
production capacity, crash recovery and team authorization are not established
by the bounded tests and are not new thresholds for the everyday-use gate.

## Protected real-client probe — 16 November 2026

Codex 0.169.0, OpenCode 2.3.0 and Claude Code 2.1.311 passed capture, retries,
expiry/branch eligibility and cross-client handover through the owner-provisioned
facade running under the service account. [All eight contract checks passed](../evaluation/phase1b/runs/20261116T072047.142646Z-real-clients/result.json).
This combined the real-client workflow with the previously proven isolated
boundary. At this run, sustained load, warmed-cache/rebuilt-index eligibility
and portable recovery remained open; later E14–E18 supply the bounded evidence
listed above. This run did not grant rollout approval.

The protected source copies matched the checkout before execution. Each client
proposed one record, received an identical retry receipt and had changed-payload
key reuse rejected. The owner accepted each proposal and retried acceptance in
their own terminal; all clients retrieved all three accepted revisions. The owner
also accepted the expired and branch-restricted fixtures. Every client excluded
the expired record from knowledge search while explicit get reported expiry;
only Codex's `feature/probe` checkout found the branch-restricted record. Claude
saved/retried a handover and had a stale update refused; Codex resumed it with the
unreviewed label and branch mismatch, then completed it; OpenCode found neither
an active handover nor a knowledge result. The final trusted snapshot contained
five accepted records and one completed handover at revision 2. Live corpus
bytes were unchanged.

All 16 checkpoint artifacts were revalidated at their original service-owned
paths for ownership and binding to this run, fixture and exact operation. The
facade was stopped before the final snapshot. Its guard and the reviewer guard
recorded only blocked `sqlite_vec` probes and zero outbound connections. The
original final assertion incorrectly required an empty blocked-import list;
the verifier was corrected to permit the expected keyword-only fallback while
still refusing inference imports and network attempts. The original client
transcripts and trusted artifacts then passed re-verification without rerunning
clients or reviewer operations; [the retained verification script](../evaluation/phase1b/runs/20261116T072047.142646Z-real-clients/reverify.py)
also checks that a FastEmbed import or outbound connection fails verification.
[Verification provenance](../evaluation/phase1b/runs/20261116T072047.142646Z-real-clients/reverification.json)
lists the original trusted artifacts. An earlier attempt stopped at sandboxed
Codex startup before making tool calls; the completed run used the existing
client logins outside that process sandbox.

Reproduce using the [owner-terminal setup](codex-setup.md#protected-real-client-probe),
then run `uv run --locked python evaluation/workflow/real_clients.py --protected-identity`.
This is one turn per client per phase against a foreground owner-terminal
service, with external client model traffic. It does not establish concurrent
protected-identity races, persistent service deployment or general capture
activation.

## Real-client facade probe — 16 November 2026

The cross-client capture contract passed through the actual Codex, OpenCode and Claude Code configurations rather than harness MCP clients. **This closes the real-client half of cross-client capture; the protected service identity, sustained load and portable recovery remain open, and no rollout gate is passed.**

[The recorded run](../evaluation/phase1b/runs/20261116T053307.631456Z-real-clients/result.json) uses [the real-client harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/real_clients.py). The facade and reviewer ran as guarded subprocesses under the E5 condition; the clients made their normal model requests. Each client connected to the facade over streamable HTTP with its own bearer token, proposed one new record with its checkout context, and, after the reviewer CLI accepted all three proposals, retrieved all three accepted record IDs in one `memory_search`.

| Client | Configuration and observed result |
| --- | --- |
| Claude Code 2.1.311 | `--model haiku` (the configured default exceeded the available credits), streamable-HTTP MCP with a bearer token, built-in tools removed by `--tools ""`; the init event listed exactly the five facade tools. Proposed and retrieved. |
| Codex 0.169.0 | `codex exec` with streamable-HTTP MCP, `bearer_token_env_var`, the five enabled tools, automatic tool approval, and shell, browser and multi-agent features disabled. Proposed and retrieved. |
| OpenCode 2.3.0 | Private server with a remote MCP entry, model `opencode-go/glm-5.3-flash`, and a `real-client` agent permitting only the five `workflow_memory_*` tools. Proposed and retrieved. |

Proposals were recorded under `agent-claude`, `agent-codex` and `agent-opencode`, the caller identities derived from their tokens. Acceptance used the reviewer CLI with a separate idempotency key per proposal and produced revision 1 for each. Every client's search returned the same three record IDs and paths (`wf/real-claude.md`, `wf/real-codex.md`, `wf/real-opencode.md`) with `accepted_by: owner`. Live corpus bytes were unchanged. The facade and reviewer guards recorded no FastEmbed or other model import attempt and no outbound connection; the only blocked import was the expected `sqlite_vec` semantic-runtime probe.

Limits: same-user disposable fixture, not the protected OS identity or service-owned storage; one proposal and one search per client, not sustained multi-client load; the clients' own model traffic is not inference-blocked; the Claude Code run used Haiku. The run exercises cross-client capture only, not handover, eligibility, retries, concurrent reviewers or portability; the extended [real-client lifecycle probe](#real-client-lifecycle-probe--16-november-2026) covers handover, eligibility and retries through the same clients.

```sh
uv run --locked python evaluation/workflow/real_clients.py
```

## Real-client lifecycle probe — 16 November 2026

The same three real clients also passed the handover, eligibility and retry contracts through the facade, closing the real-client half of those gaps. **The protected service identity, warmed-cache/rebuilt-index eligibility and sustained load remain open, and no rollout gate is passed.**

[The recorded run](../evaluation/phase1b/runs/20261116T055235.451796Z-real-clients/result.json) uses the extended [real-client harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/real_clients.py). Claude Code 2.1.311 (Haiku, `main`), Codex 0.169.0 (`feature/probe`) and OpenCode 2.3.0 (`main`) kept their per-client bearer tokens and checkout contexts.

| Contract | Observed result |
| --- | --- |
| Proposal retries | Each client proposed through the facade, repeated the same key with identical arguments and received the same proposal ID, then reused the key with a changed payload and was refused with `PAYLOAD_REUSE`. The three proposals were accepted; retrying each acceptance with its key returned the identical revision. |
| Eligibility | An expired record was absent from every client's knowledge search and excluded as `expired`, while an explicit `memory_get` reported `expired: true`. A record restricted to branch `feature/probe` appeared only to Codex; Claude and OpenCode received no result, an `environment-inapplicable` exclusion with reason `branch`, and an explicit get reporting not applicable. |
| Handover | Claude saved a handover, retried the save identically and had a stale update (`expected_revision` 99) refused. Codex saw the active handover labelled `unreviewed` with a branch mismatch, then completed it. OpenCode found no active handover and no knowledge-view trace; the stored handover was `completed` at revision 2. |

Limits: same-user disposable fixture, not the protected OS identity or service-owned storage; one turn per client per phase, not sustained load or concurrent clients; the clients' own model traffic is not inference-blocked; eligibility was served from the live store, not a warmed cache or rebuilt index. The run does not cover concurrent reviewers, deletion races or portability.

```sh
uv run --locked python evaluation/workflow/real_clients.py
```

## Native prerequisite probes — 15 November 2026

Basic Memory 1.0.0 passed the isolated storage, checksum-conflict and transaction-hook probes, but its native export and metadata filters do not supply the complete controlled workflow. **Step 2 remains incomplete; no write access or rollout gate is approved by this run.** The [capability inventory](historical-capability-inventory.md) remains the contract for the missing workflow.

The [recorded run](../evaluation/phase1b/runs/20261115T091717.382049Z/result.json) uses [the probe harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/run.py) and [a guarded native CLI entry point](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/native_cli.py). Every command runs in a fresh Python process against disposable configuration, Markdown and SQLite under the ignored run directory. Local inference-module imports are blocked before Basic Memory loads; outbound Python IPv4/IPv6 socket connections are refused, with empty isolated model caches and `HF_HUB_OFFLINE=1`. The only injected storage behaviour is a test implementation of `on_accepted_mutation()` that adds full-content revision rows and synthetic decision rows in the native transaction. These rows are test instrumentation, not human approvals or a proposal service. The installed package is unchanged.

| Probe | Observed result and limit |
| --- | --- |
| Storage without inference | Creating and updating a note with `embed: false`, reading it from later processes, search-only and full reindexing, and explicit text retrieval succeeded. The full reindex skipped the opted-out note and embedded none. Native create still attempted to import FastEmbed for its optional similar-note lookup; that import was blocked without losing the write. This proves an unavailable-inference CLI path, not a deployment-wide disable switch or long-running MCP/watcher behaviour. |
| Conflicting writes | Two sequential replacements used the same original checksum. The first succeeded; the second returned `REVISION_CONFLICT`. A create at the occupied path returned `ALREADY_EXISTS`. Neither refusal changed accepted content, revision/checksum, file bytes, journal or test history/decision rows. This is a native precondition test, not immutable proposal-base enforcement, a concurrent race test or idempotent approval. |
| Transaction hook | Successful create/update committed two complete historical contents and two synthetic decisions. An injected exception after both additional inserts rolled back the attempted note mutation, native journal entry and both additional rows; the file retained the winner. Native pre-write freshening can update bookkeeping timestamps even on refusal, so the comparison checks content/version/checksum/materialization state rather than those timestamps. |
| Search eligibility | Ordinary notes marked `proposed` or `rejected`, a completed handover, and an active handover with a past `expires_at` all appeared in default text recall, both before backup and after restore/reindex. Metadata alone does not implement separate proposal/handover views or expiry. This does not test an implemented workflow or shared cache. |
| Native OKF export | `bm okf export` produced a valid five-note bundle with current content and `log.md`. The earlier body and the synthetic decision/history data were absent. The installed export therefore needs an extension and a matching importer for a full-history round-trip; a journal log is not historical content. |
| Backup and restore | SQLite's backup API plus a quiescent Markdown copy preserved note identities, accepted content/version/checksum, native journal, both historical contents and synthetic decisions. After restoring elsewhere, `project move` bound the copied DB to the restored corpus; reindex, read and text search succeeded while the original corpus path was unavailable. This covers this fixture's native state and extra tables, not a portable import, relationships or a complete proposal/handover/review history. |

The restored database retained its old `project.path` when only the new config path was supplied. The final harness explicitly rebinds it using `project move`, checks the stored path, and renames the source corpus before restoring so success cannot depend on reading the original files. Earlier development runs without this control are not restore evidence. Raw command output, structured refusals, guard counters, the OKF bundle, backup and restored store remain in the run directory; all live corpus Markdown hashes, including pilot notes, matched before and after. No client configuration was changed and no inference provider was called successfully.

```sh
uv run --locked python evaluation/workflow/run.py
```

At E4, integration was still missing: immutable proposals bound to their original base, explicit authenticated review, separate handover lifecycle and checkout display, eligibility on every read/cache path, durable retry handling, protected canonical storage, and portable complete-history import/export. Subsequent E6–E18 implemented and tested the supported workflow; see the current status above for remaining proof. Sections 6 and 12 require an execution boundary and an alternative comparison when the addition owns most of the lifecycle. The [DrDroidLab Hindsight screening](historical-alternative-screening.md) retains its historical comparison findings. E4 justified reusing native transaction primitives, not enabling native write tools.

## MCP/watcher probe — 15 November 2026

Basic Memory 1.0.0 ran its real MCP server and file watcher end to end with inference unavailable, and the supported keyword-only fallback covered the whole path; the release offers no provider-off configuration value. **This closes the long-running MCP/watcher part of the model-independence gap for a sqlite-vec-free host; no rollout gate is passed and write access remains unapproved.**

The [recorded run](../evaluation/phase1b/runs/20261115T102626.362434Z/result.json) uses [the MCP watcher harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/mcp_watcher.py) with [a guarded server entry point](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/mcp_server_guard.py). Two fresh `bm mcp --transport stdio` server processes serve a disposable project; `sqlite_vec`, `fastembed`, `onnxruntime`, `torch`, `transformers` and `litellm` imports plus outbound IPv4/IPv6 socket connections are blocked inside the server processes, with empty isolated model caches and `HF_HUB_OFFLINE=1`. Basic Memory logs to `<config dir>/basic-memory.log`, not to the MCP stderr stream, so the fallback assertions read that log. Notes deliberately carry no `embed: false` opt-out, so this is the global path rather than the per-note exception from the CLI probe.

| Probe | Observed result and limit |
| --- | --- |
| Server and watcher without inference | Both server boots logged "Semantic search disabled: sqlite-vec package is missing … Falling back to keyword-only search". The watcher indexed externally created files with `failed_files=0` and attempted no FastEmbed import at all (guard counter 0), so with semantic disabled the embedding work is skipped, not retried. |
| Default search mode | With `BASIC_MEMORY_DEFAULT_SEARCH_TYPE` unset, a plain `bm_search` fell back to text and returned keyword results in both sessions; an explicit `mode: "vector"` search was refused with the sqlite-vec message. |
| Write degradation | `bm_write` through MCP succeeded although its optional similar-notes semantic probe failed cleanly against the blocked semantic query path — the same degradation the CLI probe saw at the import level. |
| Restart | A full server restart preserved read and default-search recall for both notes. |
| No provider-off switch | `BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER=none` crashes the CLI with `Unsupported semantic embedding provider: none`; `fastembed`, `openai` and `litellm` are the only supported values. The installation-wide lever is host-level sqlite-vec absence, which is exactly the fallback path exercised here. |

Limits: one MCP stdio client per server process and a 30 s dwell, not real model traffic; the sqlite-vec absence is simulated by blocking the import, and a deployment keeps model independence by not providing sqlite-vec. No protected execution boundary, proposal/handover workflow or portable recovery is involved. Raw server logs, guard counters, tool payloads and the provider-off crash output remain in the run directory; live corpus hashes matched before and after.

```sh
uv run --locked python evaluation/workflow/mcp_watcher.py
```

## Workflow service core probe — 15 November 2026

The approved Option A workflow service is implemented as [the `workflow/` package](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/service.py) — `wf_*` tables for the project registry, immutable proposals, durable revisions, decisions, handovers and retry state in the same SQLite store, with accepted knowledge written as native notes through the accepted-note mutation service. [The core probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/workflow_core.py) runs the real service in-process against a disposable store under the E5 condition (inference imports and outbound sockets blocked; the semantic runtime is turned away by the absent sqlite-vec extension). **This proves the implemented core contract; the reviewer execution boundary, portable export/import and concurrent load remain open, and no rollout gate is passed. The facade for the three clients is proven separately in [the facade/cross-client probe](#facade--cross-client-probe--15-november-2026).**

Recorded run: [20261115T125538.480715Z-workflow-core](../evaluation/phase1b/runs/20261115T125538.480715Z-workflow-core/result.json).

| Contract behaviour | Observed result |
| --- | --- |
| Proposals | Propose is retry-idempotent (same key returns the original proposal); key reuse with a changed payload is rejected. Proposals and handovers are never notes: no proposal, rejection or handover token appears in native recall from a fresh process. |
| Atomic acceptance | Acceptance wrote the immutable revision (full body), the accepted decision, the supersession of the previous revision and the proposal status inside the note transaction; the acceptance retry returns the original resulting revision. |
| Pending edits | An open proposal and a rejected proposal both left the accepted body, its recall and the revision set unchanged. |
| Stale approval | Two proposals on revision 1: accepting the first created revision 2; the second conflicted and stayed pending. The service exposes no checksum argument at all, so a freshly read checksum cannot unlock a stale acceptance. |
| New target | Accepting a proposal whose reserved path is occupied was refused (`TargetExistsError`) and left the proposal pending. |
| Rollback | An injected hook failure rolled back the note, file, revision, decision, proposal status and recall completely. |
| Handovers | Save and resume without reviewer access; unreviewed label with branch/commit fields; stale update (`expected_revision` 99 vs 1) failed; a correct update bumped the revision; completion and a past `expires_at` both left the active view (expiry checked at read time); completed/expired handovers never appear in knowledge recall. |
| Model independence | Zero inference-module import attempts; only the semantic-runtime probes (`sqlite_vec`) were blocked; no embedding model downloaded; live corpus hashes unchanged. |

## Facade / cross-client probe — 15 November 2026

The MCP facade from the [workflow-service design sketch](historical-workflow-design.md#agent-facade-mcp-tools-for-the-three-clients) is implemented as [workflow/facade.py](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/facade.py): a FastMCP streamable-HTTP server exposing exactly `memory_search`, `memory_get`, `memory_propose`, `memory_save_handover` and `memory_complete_handover`, with bearer-token callers (agent and reviewer roles), project resolution from the caller's checkout context against the registered project's approved checkouts (never a directory path), and facade-level eligibility on the knowledge view. Every search, mutation and explicit get is bound to the resolved project: the knowledge view routes native full-text search through the resolved project and excludes records of another registered project, handover mutations deny a target that belongs to a different project, and a foreign explicit get is denied. Environment restrictions support `branch`, `commit` and `tool_versions` and are enforced fail closed — an unsupported restriction key, or a restriction the checkout context cannot verify, makes the record inapplicable instead of unrestricted. Note paths are unique per project, not globally: each project's corpus may hold the same relative path as another project's, and the knowledge view resolves each hit within the resolved project. `memory_get` requires a checkout context — the argument is schema-required, so a get without one is refused before execution — resolving the project, denying foreign objects and reporting applicability. Acceptance and rejection run in [the reviewer CLI](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/reviewer.py) as its own process through the same transaction hook. [The facade/cross-client probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/facade_cross_client.py) connects three independently authenticated agent MCP clients over HTTP to one facade process with two registered projects, plus the reviewer CLI subprocess, both under the E5 condition. **This proves the facade contract with three MCP clients; the protected execution boundary (separate OS identity, filesystem/backend denial matrix), the three real client configurations (Codex/OpenCode/Claude Code), concurrent multi-client load and portable export/import remain open, and no rollout gate is passed.**

Recorded run: [20261115T144630.503166Z-facade-cross-client](../evaluation/phase1b/runs/20261115T144630.503166Z-facade-cross-client/result.json).

| Contract behaviour | Observed result |
| --- | --- |
| Denials | An unissued token and the reviewer token on an agent tool were both denied before any operation ran; a checkout context outside the approved list, and a missing checkout context, failed project resolution; an explicit get, a handover completion and a handover update targeting another registered project were each denied as project mismatches. |
| Project isolation | With two registered projects, each checkout context resolved to its own project and route: the other project's client retrieved only its own accepted record and saw none of the main project's, the main clients saw none of the other project's, and foreign `memory_get` was denied — with checkout supplied as `PROJECT_MISMATCH`, without checkout as a schema-required-argument refusal. The same relative note path existed as two separate records, one per project, each served only to its own project's callers. |
| Cross-client capture | Client A proposed a new record; clients B and C saw nothing; after reviewer acceptance both retrieved revision 1 with snippet, revision, sources, acceptance provenance; `memory_get` returned the current revision and history. |
| Pending edits | B's open proposal and its rejection left the accepted body, the other clients' recall and the revision set unchanged; `memory_get(view=proposals)` exposed the rejected proposal with its decision explicitly. |
| Stale approval | Two proposals on revision 1 from A and C: accepting A's created revision 2; C's conflicted (`REVISION_CONFLICT`), stayed pending, and a fresh acceptance attempt with a new key conflicted again — the service offers no checksum argument at all. |
| Supersession | After acceptance of revision 2 the retired body token no longer matched at all (the body left the note file), the same structural behaviour the native probe [E4] showed; proposals and handovers never appear in the knowledge view. |
| Handover | A saved a handover; B resumed it without reviewer access; the handover view labelled it unreviewed and displayed the checkout mismatch per caller (A: no mismatch, B: branch and commit mismatch); A's stale update failed; B's completion removed it from every active view; a past `expires_at` handover was excluded at read time and visible only through `memory_get`; handover tokens never matched the knowledge view. |
| Retries | Propose, handover update and reviewer acceptance retries returned the original results; key reuse with a changed payload was rejected; idempotency is scoped to the caller — B reusing A's key with the same payload created its own (rejected) proposal. |
| Eligibility | A revision with a past `expires_at` was excluded from the knowledge view for every client while `memory_get` reported the expired state; a record restricted to branch `feature/probe` appeared for B and was excluded as environment-inapplicable for A and C; a commit-restricted record appeared only for the caller whose checkout commit matched; a record with an unsupported restriction key (`platform`) was excluded as `unsupported-environment-restriction` for every caller — fail closed, never treated as unrestricted. `memory_get` with a checkout context reported the environment restriction, its applicability and the reason for inapplicability while the record stayed explicitly readable. |
| Restart | Terminating the facade process and starting a new one preserved recall (revision 2) and the exclusions. |
| Model independence | Zero inference-module import attempts in the facade server and the reviewer processes; only `sqlite_vec` semantic-runtime probes were blocked; no embedding model downloaded; live corpus hashes unchanged. |

Limits: three MCP clients against one facade process with two registered projects under blocked inference, not real model traffic; the reviewer runs as a guarded CLI subprocess with its own store and notes client, but the protected boundary (separate OS identity, filesystem/backend denial matrix) is still unproven; the three real client configurations are not yet connected to the facade. Raw per-call payloads, reviewer outputs and guard counters remain in the run directory.

```sh
uv run --locked python evaluation/workflow/facade_cross_client.py
```

## Store upgrade probe — 15 November 2026

The per-project path uniqueness in `wf_record` cannot reach stores created earlier, because `CREATE TABLE IF NOT EXISTS` never alters an existing table: an old store keeps the global `UNIQUE` on `file_path` and rejects the same relative note path in a second project. [WorkflowStore now migrates on open](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/store.py): when the existing `wf_record` table lacks the `UNIQUE (project_uuid, file_path)` constraint, it rebuilds the table in one transaction, preserving every row (previous rows were globally unique, so they cannot violate the new per-project constraint), and re-opening a migrated store is a no-op. [The store upgrade probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/store_upgrade.py) builds a store with the recorded pre-upgrade schema, seeds project/record/revision/operation rows, opens it with the current code, and verifies the upgrade end to end under the E5 condition.

Recorded run: [20261115T144544.109099Z-store-upgrade](../evaluation/phase1b/runs/20261115T144544.109099Z-store-upgrade/result.json).

| Upgrade behaviour | Observed result |
| --- | --- |
| Data preservation | Every seeded `wf_*` row compared byte-identical before and after the migration; re-opening the migrated store changed nothing. |
| Constraint | The rebuilt table's DDL carries `UNIQUE (project_uuid, file_path)` and no global path uniqueness; a duplicate path within one project still fails with the composite-constraint error, while the same relative path in the other project inserts. |
| Referencing rows | `wf_revision` rows kept working against the rebuilt table (insert and read through the store methods). |
| End-to-end acceptance | The real service accepted `wf/shared-legacy.md` — the seeded main project's relative path — in the second project through the reviewer CLI subprocess; the two projects own distinct records under the identical path, the second project's corpus received the note, and the first corpus was untouched. |
| Model independence | Zero inference-module import attempts; only `sqlite_vec` semantic-runtime probes were blocked in the acceptance process; no embedding model downloaded; live corpus hashes unchanged. |

Limits: a store-level upgrade from the recorded pre-upgrade schema with seeded workflow data plus one real acceptance in the second project, not a full end-to-end rerun of the facade probe on a migrated store; export/import and the protected boundary remain open.

```sh
uv run --locked python evaluation/workflow/store_upgrade.py
```

## Review-boundary probe — 15 November 2026

Deletion is now an authorized reviewer operation ([`wf delete` in the reviewer CLI](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/reviewer.py), [service](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/service.py)): the deletion intent with its payload hash is persisted as the operation's first result before any destructive step, so an interruption can never turn a changed-payload retry into a different successful deletion — the resume checks against the recorded hash. The note is then deleted through the note-serving API against the current revision's `native_checksum` (CAS — a drifted note is refused with `REVISION_CONFLICT` and the record stays), and the record's revision, proposal and decision rows go in one store transaction that finalizes the receipt. Both steps resume idempotently: an already-deleted note is skipped, already-deleted rows delete as no-ops, and the `wf_operation` receipt keeps the audit trace. The core probe [E6] covers both interruption points — before the note deletion and after it — including the rejected changed-payload resume.

[The review-boundary probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/review_boundary.py) is the authorization proof for the protected reviewer access. It runs entirely as the agent's identity; every trusted step — fixture setup, facade serving, reviewer acceptance, deletion and verification — runs in the owner's own terminal with a password, from a runtime copy that the service identity owns and agents cannot modify ([boundary_provision.sh](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/boundary_provision.sh) copies the Python environment, the `workflow/` package and the service-side runner into `/path/to/service-home/boundary-runtime`, `chown`s it and removes group/other write; no sudoers rule is installed, so agent sessions hold no reviewer authority and cannot run reviewer operations or inject code into the service identity). Provisioning requires removal of the legacy `boundary_service.sh` sudoers authorization and checks that noninteractive execution as the service identity is denied. The protected runner’s `configure` command publishes `~/boundary-evidence/config.json`; select it explicitly with `review_boundary.py --protected-identity`. The default disposable mode and the integration test use a local, noninteractive fixture even when trusted configuration exists. The probe validates the service account, configuration, runtime paths and evidence directory, including every ancestor’s ownership, mode and agent write access. Runtime validation recursively checks contents, package symlink targets and `.pth`/`.egg-link` dependency paths; writable external dependencies and executable `.pth` hooks are rejected. Provisioning performs this inspection before starting the copied interpreter. In identity mode the probe prints shell-quoted owner commands that write atomic artifacts directly into the service-owned evidence directory. Each artifact is checked against the probe run, fixture and exact operation; checkout copies are archival only. The facade remains running through final recall, then stops before the final verification snapshot captures its guard counters. Between checkpoints the probe runs, as the agent identity, the denial matrix against the protected fixture explicitly: direct note overwrite, append, creation, deletion and atomic replacement; direct SQLite mutation, journal/WAL and backup tampering; reviewer-credential reads; native Basic Memory CLI writes and deletes; and the reviewer CLI with a forged `--reviewer`. The classifier ([boundary_checks.py](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/boundary_checks.py)) accepts only actual permission/read-only conditions — `EACCES`, `EPERM`, `EROFS`, an SQLite read-only error, or an SQLite "unable to open" error corroborated by an `EACCES` stat on the same path plus the trusted ownership report; any other error (missing path, cross-filesystem rename, database lock, missing table, CLI failure without permission evidence) is an invalid attempt and fails the run. Positive controls prove the authorized path: the agent writes its scratch directory and proposes through the facade; the trusted reviewer accepts and publishes against the same protected store and deletes a record idempotently; the trusted side verifies, before and after the attempts, that note bytes and logical `wf_*` state are unchanged apart from the authorized positive-control changes. One verdict is built from every check — surface denials (MCP exposes exactly the five `memory_*` tools, reviewer-token and unknown-token calls are denied, backend HTTP has no reviewer route), positive controls, state comparison and every denial attempt — and any exercised check that fails makes the probe exit nonzero, so the integration test catches it; skipped checks (identity mode unavailable) are distinguished from failed ones, and the verdict never claims proof because an identity merely exists.

Earlier disposable run: [20261115T153749.725974Z-review-boundary](../evaluation/phase1b/runs/20261115T153749.725974Z-review-boundary/result.json) — the trusted control path was not yet set up for this run, so it exercised the identity-independent surface against a probe-owned fixture and recorded the OS-enforced leg as **unproven, never passed** (skipped, with the reason recorded). Surface results: MCP tool-surface refusals for `memory_accept`/`memory_delete`/`memory_reject`, reviewer-token and unknown-token denials, backend route 404, state unchanged during the attempts, authorized publish and authorized idempotent deletion through the reviewer CLI, zero inference-module import attempts, no embedding model downloaded, live corpus unchanged. Regression tests cover verdict prerequisites, protected evidence ownership and replacement paths, artifact binding, shell argument preservation and strict denial classification ([trust tests](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/tests/evaluation/workflow/test_boundary_trust.py), [classifier and integration tests](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/tests/evaluation/workflow/test_workflow_integration.py)). That disposable run did not establish the protected OS leg; the owner-provisioned run below supplies that evidence.

Owner-provisioned run: [20261115T181606.813443Z-review-boundary](../evaluation/phase1b/runs/20261115T181606.813443Z-review-boundary/result.json) — **OS-enforced boundary proven** for this isolated deployment: all 37 checks passed, with no failed or skipped checks. The fixture was owned by service account; agent-side filesystem, SQLite, native CLI, forged reviewer CLI, MCP tool-surface, token/role and backend-route attempts were denied. Owner acceptance published a retrievable revision; authorized deletion removed the second record and its retry was idempotent. Trusted snapshots verified no changes during denied attempts and only authorized final changes. There were zero inference-module import attempts, no embedding downloads, and the live corpus stayed unchanged. All seven service-owned checkpoint artifacts were rechecked for protected ownership and binding to the probe run, fixture and exact operation; the protected workflow/runner/checker sources matched the checkout at commit `b0f4af9`.

Runtime: Basic Memory 1.0.0 under standalone CPython 3.12.16, with MCP 2.3.0, using `/path/to/service-home/boundary-runtime/venv-protected/bin/python`. The agent-side probe used the checkout's existing Python 3.14 environment. Initial provisioning created the account and protected code copy, then correctly rejected the copied venv because it retained a user-owned Homebrew interpreter. The owner copied the existing project-local standalone Python into the protected runtime and created a separate venv; no system/Homebrew ownership was changed. Substitute the provisioned service account and home directory in the examples below. The following owner-terminal commands describe that additional setup; the final command installs the locked dependencies:

```sh
runtime=/path/to/service-home/boundary-runtime
sudo ditto "$PWD/.python/cpython-3.12.16-macos-aarch64-none" "$runtime/python"
sudo chown -R workflow-service-account "$runtime/python"
sudo chmod -R go-w "$runtime/python"
sudo -H -u workflow-service-account "$runtime/python/bin/python3.12" \
  -m venv --copies "$runtime/venv-protected"

requirements="$PWD/evaluation/phase1b/runs/boundary-requirements.txt"
uv export --locked --no-dev --no-emit-project \
  --format requirements.txt --output-file "$requirements"
sudo -H -u workflow-service-account "$runtime/venv-protected/bin/python" \
  -m pip install --require-hashes -r "$requirements"
```

This standalone-runtime setup is manual; `boundary_provision.sh` still copies the checkout venv and does not automate it. The standalone runtime, installed dependency trees, protected code and their ancestors passed ownership, mode, import-path and agent write-access validation. The expected `sqlite-vec` warning is the guarded keyword-only fallback.

For each protected run, use a fresh fixture and keep the facade running in terminal A:

```sh
python="$runtime/venv-protected/bin/python"
runner="$runtime/code/evaluation/workflow/boundary_service.py"
fixture_id="owner-$(date +%Y%m%dT%H%M%S)"
fixture="/path/to/service-home/boundary/$fixture_id"
sudo -H -u workflow-service-account "$python" "$runner" setup "$fixture_id"
sudo -H -u workflow-service-account "$python" "$runner" configure "$fixture" --port 8765
sudo -H -u workflow-service-account "$python" "$runner" serve "$fixture" --port 8765
```

Run the probe as the agent user in terminal B and execute its printed owner commands in terminal C. Leave both the facade and probe running at checkpoints; at `verify-final`, stop the facade before running the final verification command.

```sh
uv run --locked python evaluation/workflow/review_boundary.py --protected-identity
```

Limits: this proves the exercised boundary for the disposable protected fixture, with an owner-terminal facade rather than a persistent service. The three actual client configurations, concurrent multi-client load, full workflow export/import and recovery, and the everyday-use evaluation remain open; this run alone does not pass the former rollout gates or enable capture.

## Concurrent reviewer probe — 15 November 2026

Independent reviewer processes passed synchronized races for competing edits, competing creates at the same path, and duplicate acceptance with the same idempotency key. The [recorded run](../evaluation/phase1b/runs/20261115T182752.432673Z-reviewer-races/result.json) uses [the race harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/reviewer_races.py) against a disposable Basic Memory 1.0.0 store. Each worker calls the real reviewer entry point with its own SQLite connection and notes client; a barrier immediately before the native write ensures both processes have already captured the proposal's stored base before either can commit. Per-worker artifacts record the process IDs, write inputs, results and guard counters.

Competing edits both used revision 1's checksum: exactly one committed revision 2 and the other returned `REVISION_CONFLICT`. Competing new-record proposals both used `overwrite=False`: exactly one committed revision 1 and the other returned `ALREADY_EXISTS`, without creating a stray workflow record. Both losers remained pending with no decision or acceptance receipt. Duplicate same-key acceptance returned the identical revision and checksum to both callers, with one revision, decision and receipt. Retrying every operation from fresh reviewer processes preserved all record, revision, proposal, decision and retry-ledger rows and the canonical file bytes. History, native checksums, materialized file hashes and keyword recall matched the winners; losing content was absent from recall. Inference imports and outbound Python socket connections were blocked in the parent and workers: zero inference attempts, no model downloads, live corpus unchanged.

This covers the exercised reviewer-process races, including concurrent duplicate retries. It does not establish actual Codex/OpenCode/Claude Code configurations, races under the protected service identity, sustained multi-client load, concurrent deletion, warmed-cache/rebuilt-index eligibility or portable recovery. No rollout gate is passed.

```sh
uv run --locked python evaluation/workflow/reviewer_races.py
```

## Phase-plan change — 15 November 2026

The recommendation to run an early trial for roughly two weeks before spending effort on controlled capture was replaced by the everyday-use gate recorded in [the architecture document, section 13](../evaluation/harness-independent-shared-memory.md#13-acceptance-criteria-and-rollout-gates): minimum observation of at least 10 recall-relevant work sessions across at least 2 repositories over at least 7 days; at least 3 documented useful recalls; at most 2 missed recalls of accepted content; fewer false recalls than useful recalls; no retrieval abandoned because of latency; maintenance effort below the documented saved investigation time; discovered wrong accepted entries corrected or captured as proposals before the evaluation closes; and an early-failure verdict allowed after 10 recall opportunities without a single useful recall. The thresholds were approved and recorded on 15 November 2026, before any evaluation against them. Preparing the gap inventory may start in parallel; enabling capture remains gated on both the everyday-use result and the unchanged capture gates.

## Global OpenCode and Claude Code checks — 15 November 2026

OpenCode's existing global config symlink was preserved and its dotfiles source updated with the Basic Memory server, `codemode: false`, `HF_HUB_OFFLINE=1`, the existing evaluation timeouts, and ordered permissions denying `basic_memory_*` except search/read. Claude Code received a user-scoped server registration in `~/.claude.json` and the existing two allow/ten deny rules in `~/.claude/settings.json`. Existing client settings were preserved. The memory-repo evaluation configurations remain project-local.

Both clients were checked from a separate checkout with ordinary tools enabled. OpenCode used its global MCP configuration and permissions, with only a temporary capture plugin injected. The plugin recorded the unchanged effective tool names and connection status, then threw before provider invocation. The connected inventory contained exactly `basic_memory_bm_search` and `basic_memory_bm_read` from Basic Memory, with ordinary tools retained. The private server was stopped afterward. The dotfiles repository's existing policy checks also passed: 7 tests and 131 subtests covering install prompts and shell policies.

Claude Code 2.1.311 retained normal global/project settings discovery and global MCP registration, with a temporary `UserPromptSubmit` hook exiting 2 before model invocation. The first check reported `basic_memory` as `pending` with no memory tools. A second check with the temporary `CLAUDE_CODE_MCP_STARTUP_WAIT_MS=120000` environment override reported the server connected and exactly `mcp__basic_memory__bm_search` and `mcp__basic_memory__bm_read` exposed from Basic Memory. The startup-wait override was not persisted globally. No model request or note-write call was made by either check. This verifies cross-repository connectivity and tool restrictions once; ordinary-session and first-turn recall reliability remain unproven.

[Saved inventories and verification summary](../evaluation/global/runs/20261115T080835.730608Z/) are local ignored artifacts, including the capture script. The everyday-use practical-value trial is now prepared in the [observation log](../evaluation/observations.md), but remains unevaluated.

## Global Codex configuration check — 15 November 2026

The existing Basic Memory server settings were added to `~/.codex/config.toml` for the cross-repository practical trial, preserving other global settings. The project-local configuration remains the isolated evaluation runner's input. Both allow only `bm_search` and `bm_read`, with `required = true`, 120-second startup/tool timeouts, and `HF_HUB_OFFLINE=1`.

A manual check from a separate checkout confirmed that `codex mcp list` discovers `basic_memory`. A fresh ephemeral Codex app-server thread rooted in that checkout then returned exactly `bm_search` and `bm_read` through `mcpServerStatus/list`. No model turn or note-write call was made. This confirms global discovery and the live tool allowlist once; it does not establish ordinary-session recall reliability or complete the practical trial. This check was observed in the configuration session; no run artifacts were saved in this repository.

Commands below run from the project root. Raw run artifacts are retained locally under ignored `evaluation/*/runs/` directories; their links require those artifacts and are not available in a fresh clone.

## Claude Code recall run — 14 November 2026

[The recorded run](../evaluation/claude/runs/20261114T124210.466630Z/) used Claude Code 2.1.325 with its account-default model `system.ai.claude-opus-5-5` and Basic Memory 1.0.0. The session's own `init` event listed exactly `mcp__basic_memory__bm_search` and `mcp__basic_memory__bm_read` with the server connected: `--tools ""` removed every built-in tool and the project permission deny list removed the other ten Basic Memory tools. The transcript contains 22 text searches and 1 read, with no tool errors, permission denials, or subagent activity. Corpus bytes were unchanged.

The [score](../evaluation/claude/runs/20261114T124210.466630Z/score.json) was **19/20 recall hits at five, 2/2 no-answer questions recognized**. The miss was the duplicate-retry question: the query `duplicate retries` returned no results and the client did not report missing evidence. The run was not tuned or repeated to improve the score. Contrary to the prompt, the client prefixed the requested JSON array with one line of prose; the verifier accepts exactly one fenced JSON block. The first search passed `all_projects: true` and the other 21 passed `project: "main"`; only the `main` project exists. Search latency between tool-use and tool-result stream events was 59–655 ms, median 74 ms. The whole turn took 58 s. [Raw stream events](../evaluation/claude/runs/20261114T124210.466630Z/events.jsonl), [prompt](../evaluation/claude/runs/20261114T124210.466630Z/prompt.txt), [inventory](../evaluation/claude/runs/20261114T124210.466630Z/effective-tools.json), and the [results](../evaluation/results-claude.json) are preserved.

The [startup run](../evaluation/claude/runs/20261114T124340.847047Z/startup-result.json) used the Codex startup task and instructions with no mention of memory or retrieval. Claude Code independently made 4 searches and 9 reads, including `memory-20`, and advised against syncing the live SQLite database while separating accepted proposal guidance from what still needs testing. Its searches omitted `mode` and `output_format`, so this is not an explicit-text-mode run. The [outage run](../evaluation/claude/runs/20261114T124203.409307Z/outage-result.json) substituted `/usr/bin/false` for the server command: Claude Code reported `basic_memory` as `failed` with no memory tools, and has no setting equivalent to Codex's `required = true` that refuses the session. The preflight hook stopped that run before a model request, so the model's behaviour without the server was not observed.

As with the other clients, this is explicitly prompted recall plus one unprompted startup check in an isolated empty workspace, with CLAUDE.md files and auto-memory disabled; it does not establish reliability in an ordinary checkout.

```sh
uv run --locked python evaluation/claude/run.py
uv run --locked python evaluation/claude/run.py --startup
uv run --locked python evaluation/claude/run.py --outage
```

## OpenCode recall run — 14 November 2026

[The recorded run](../evaluation/opencode/runs/20261114T111128.100130Z/) used OpenCode 2.3.0 with `opencode-go/glm-5.3-flash` and Basic Memory 1.0.0 (MCP server over FastMCP 4.1.3). The plugin-captured tool snapshot sent to the model contained exactly `bm_search` and `bm_read`, and the MCP server was connected; no mutation or project-management tool was exposed to the model or executed. The transcript contains 22 text searches and 0 reads, with no tool errors. Unlike the Codex run, the client answered all questions from the returned search snippets without reading any note; the evaluator verified every returned permalink against the local corpus frontmatter afterwards. Because no note was read, no source revision was exposed inside this run itself; the engine serving the run was verified separately and afterwards (see the [evidence verification](#engine-served-evidence-verification--14-november-2026)), which reproduced the same server command and confirmed that the engine serves every one of the 20 notes byte-identically to the corpus with the accepted `source_revision`. Corpus bytes were unchanged.

The [score](../evaluation/opencode/runs/20261114T111128.100130Z/score.json) was **20/20 recall hits at five, 2/2 no-answer questions recognized**. The run was not tuned or repeated to improve the score. Search-call latency was 47–270 ms, median 70 ms; these timings exclude model reasoning. [Raw client events](../evaluation/opencode/runs/20261114T111128.100130Z/client-response.txt), [prompt](../evaluation/opencode/runs/20261114T111128.100130Z/prompt.txt), [versions](../evaluation/opencode/runs/20261114T111128.100130Z/client-version.json), and the [results](../evaluation/results-opencode.json) are preserved.

The recorded runs predate the inventory preflight added after review; their live snapshots were verified retrospectively. The repaired inventory-only preflight was exercised successfully without model invocation or a new scored recall run.

This was explicitly prompted architecture recall in a second client. It does not change the Codex score or pass the earlier gate. The evaluated session ran in the real checkout with file, shell, web, and other tools denied by agent permission rules, and the evaluation plugin additionally stripped every other tool from the outgoing model request; this is workflow isolation under a trusted owner, not an OS confidentiality boundary, and OpenCode session records live in the shared service data directory outside the project.

## OpenCode startup check — 14 November 2026

The [startup run](../evaluation/opencode/runs/20261114T111405.908212Z/startup-result.json) used a fresh session and the same practical task about continuing work across two laptops, with no instruction to recall or search memory in the prompt (asserted by the checker) or the agent instructions. OpenCode independently made 4 searches and 4 reads, including `memory-20`, and advised against syncing live SQLite/WAL files. Its response distinguished accepted proposal guidance from capabilities that still need validation. The effective inventory remained exactly `bm_search` and `bm_read`, and corpus bytes were unchanged. [Raw client events](../evaluation/opencode/runs/20261114T111405.908212Z/client-response.txt), and the [prompt](../evaluation/opencode/runs/20261114T111405.908212Z/prompt.txt) are preserved.

```sh
uv run --locked python evaluation/opencode/run.py --startup
uv run --locked python evaluation/opencode/verify_startup.py RUN_DIRECTORY
```

As with Codex, this demonstrates unprompted retrieval once in a restricted session; it does not establish reliability in an ordinary checkout.

## OpenCode outage check — 14 November 2026

The [recorded run](../evaluation/opencode/runs/20261114T131528.239541Z/outage-result.json) substituted `/usr/bin/false` for the Basic Memory server command by injecting a disposable configuration through `OPENCODE_CONFIG_CONTENT` — the live configuration and store were not touched, and the run stayed in the real checkout so config resolution matched the recorded runs. The injected configuration added a `memory-outage` agent with deny-all permissions and an [outage capture plugin](../evaluation/opencode/outage-plugin/index.ts) that, unlike the evaluation capture plugin, records what the model receives without rejecting: it strips every tool from the outgoing request and snapshots the MCP server status.

Both model requests (a readiness turn and the [observed turn](../evaluation/opencode/runs/20261114T131528.239541Z/observed.stdout), which asked how the live SQLite database should be handled across two laptops) were sent with **no tools at all**; the plugin snapshots show `basic_memory` as `failed` in both, no tool executed, and corpus bytes were unchanged. The connect API returned success while the server status stayed `failed`, so the outage is visible through the server status. OpenCode has no setting equivalent to Codex's `required = true`: the session starts during the outage, and the service state is what makes the outage visible.

The model's behaviour without the service was observed directly, which the Claude outage run could not do because its preflight hook stops the turn before any model request. In this run the model said it had no `bm_search`/`bm_read` tools available and then emitted a textual pseudo-invocation of `use_mcp_tool` in its prose — a hallucinated call format that executed nothing — instead of explicitly reporting that the evidence was missing. With the evaluation's standard, that response does not meet the recognized-missing-evidence bar; a service outage must be visible to the operator, and here it also changed client behaviour in a way that a scored run should treat as missing evidence rather than an attempted call.

```sh
uv run --locked python evaluation/opencode/run.py --outage
```

Two earlier failed attempts are retained alongside the recorded run: one used a disposable workspace under the ignored `evaluation/*/runs/` tree, where OpenCode's config resolution (which follows the git project root) never saw the injected configuration and the client failed with `Agent not found`; the second ran fully but crashed in its own verification step before writing `outage-result.json`.

## Embedding-model download during the OpenCode setup — 14 November 2026

The OpenCode server configuration initially omitted `HF_HUB_OFFLINE`. The `bm` launcher does not set it either — Codex's configuration supplies it under `[mcp_servers.basic_memory.env]`. The first OpenCode-spawned server therefore ran background embeddings and FastEmbed downloaded `BAAI/bge-small-en-v1.5` (Qdrant ONNX weights) into the project-local `.models` cache: one 66,465,124-byte blob plus small metadata files, fetched through the Hugging Face xet path at 12:05 local time, before the scored run. The scored run's startup log then showed 20 embeddings across 20 chunks; its explicit `mode="text"` searches did not use the vector index. Indexing wall time and memory use were not measured. Details and the process-environment evidence are in [server-env-check.txt](../evaluation/opencode/server-env-check.txt).

After adding `HF_HUB_OFFLINE: "1"` to the OpenCode server configuration, a cold-cache control experiment with the same environment confirmed the flag is effective: FastEmbed never downloaded and failed with `local_files_only=True` (`Could not find the model tar.gz file ... and local_files_only=True`), matching the recorded Codex behaviour; the cache stayed 0 B. The downloaded weights remain in the project-local `.models` cache. The template and the ignored local configuration now both carry the environment entry. [Indexing wall time and memory use were subsequently measured](#indexing-cost-measurement--14-november-2026).

## Recorded result — 14 November 2026

[The recorded run](../evaluation/codex/runs/20261114T063508.436677Z/) used Codex CLI 0.169.0 with `gpt-6-astra` and Basic Memory 1.0.0. Its [effective inventory](../evaluation/codex/runs/20261114T063508.436677Z/effective-tools.json) contained only `bm_search` and `bm_read`, both marked read-only. The transcript contains 22 text searches and 19 reads, with no mutation calls or tool errors. Corpus bytes were unchanged.

The [score](../evaluation/codex/runs/20261114T063508.436677Z/score.json) was **19/20 recall hits at five, 2/2 no-answer questions recognized**. The missed startup-retrieval question used the exact phrase `"task start"`, which returned no results; the client reported missing evidence. The run was not tuned or repeated to improve the score. Search-call latency was 47–411 ms, median 77 ms; these timings exclude model reasoning and note reads.

This was explicitly prompted architecture recall in one client. The separate startup and recovery checks below do not change its score. At this run the other clients and engine-served source evidence were untested; the subsequent client and evidence-verification sections record those results. Direct inspection of the linked architecture source during client retrieval and everyday practical value are distinct claims. Note acceptance and this score do not establish capture, lifecycle, or authorization capabilities.

## Startup and outage checks — 14 November 2026

The [startup run](../evaluation/codex/runs/20261114T103614.063962Z/startup-result.json) used a fresh ephemeral session and a practical task about continuing work across two laptops, with no instruction to recall or search memory. Codex independently made three searches and seven reads, including `memory-20`, and advised against syncing live SQLite/WAL files. Its response distinguished accepted proposal guidance from verified implementation. The effective inventory remained exactly `bm_search` and `bm_read`, and corpus bytes were unchanged. [Raw events](../evaluation/codex/runs/20261114T103614.063962Z/events.jsonl), [prompt](../evaluation/codex/runs/20261114T103614.063962Z/prompt.txt), and [response](../evaluation/codex/runs/20261114T103614.063962Z/client-response.txt) are preserved.

This demonstrates unprompted retrieval once in an isolated workspace with other task tools disabled. It does not establish reliability in an ordinary checkout. All three searches omitted `mode`; the launcher defaults to text, but this is not an explicit-text-mode scored run.

The [outage run](../evaluation/codex/runs/20261114T103659.995645Z/outage-result.json) substituted `/usr/bin/false` for the MCP command only in the disposable evaluation configuration. With `required = true`, Codex returned a visible required-server initialization error and refused to create the session before any model turn. Corpus bytes were unchanged; the live configuration and store were not replaced. This covers service unavailability at startup, not connection loss during an existing task. The earlier failed attempts are retained alongside the completed runs.

Reproduce with the existing environment and Codex login:

```sh
uv run --locked python evaluation/codex/run.py --startup
uv run --locked python evaluation/codex/run.py --outage
```

## Document restore drill — 14 November 2026

The [recorded drill](../evaluation/recovery/runs/20261114T103738.568274Z/result.json) passed: 21 documents restored byte-for-byte, all 20 notes read with identical metadata, and all 20 returned by text search after rebuilding a fresh index. Original project documents remained unchanged.

```sh
uv run --locked python evaluation/recovery/run.py
```

The drill archives the 20 accepted notes and their linked architecture source, verifies restored bytes, and runs `reindex --full --search --project main` against a new isolated SQLite store. It then reads all notes to compare every frontmatter field, checks source links, and verifies all 20 notes appear in a text search. Timestamped recovery directories preserve the archive, hash manifest, isolated configuration, command outputs, and result. No live SQLite/WAL database is copied or replaced. This checks document and metadata recovery, not portability of engine database UUIDs or future revision history. Two same-day reruns ([one](../evaluation/recovery/runs/20261114T121816.427372Z/result.json), [two](../evaluation/recovery/runs/20261114T122159.358030Z/result.json)) passed with identical results; the pilot notes added later under `evaluation/corpus/pilot/` are outside the drill's top-level corpus glob and remain untested by it.

## Engine-served evidence verification — 14 November 2026

The [recorded verification](../evaluation/evidence/runs/20261114T130450.173545Z/result.json) reproduced the exact server command the evaluated clients used (`./bm mcp --project main`, Basic Memory 1.0.0 over FastMCP 4.1.3) and called only `bm_search` (explicit `mode="text"`, `page_size=5`, `output_format="json"`) and `bm_read`. For each of the 20 corpus notes: a title query returned the note's permalink — identical to its stable frontmatter `id` — within the first five results with the matching title; the served `bm_read` text was byte-identical to the corpus file, exposed `id`, `permalink`, and the accepted `source_revision`, and its `source_uri` resolved to the architecture document whose SHA-256 matches that revision. Corpus hashes were unchanged before and after. [Per-note served reads](../evaluation/evidence/runs/20261114T130450.173545Z/read-memory-01.md) and [search results](../evaluation/evidence/runs/20261114T130450.173545Z/search-memory-01.json) are preserved alongside the [manifest](../evaluation/evidence/runs/20261114T130450.173545Z/corpus-hashes.json). Round-trip latency was 37–544 ms, median 38 ms, including model-free search and read.

This closes the earlier evidence gate: results expose stable identity and source revision, and the source is available for inspection. In the Claude and Codex runs the verifiers already confirmed every read's served `source_revision`; this check adds the engine-level confirmation for all 20 notes, including the notes the OpenCode recall run reached only through search snippets.

```sh
uv run --locked python evaluation/evidence/run.py
```

## Indexing cost measurement — 14 November 2026

The [recorded measurement](../evaluation/indexing-cost/runs/20261114T132157.424149Z/result.json) ran `basic-memory reindex` three times against isolated SQLite stores holding byte-identical copies of the 20 accepted notes, with the pre-cached project-local `.models` weights and `HF_HUB_OFFLINE=1` (no download; the live store was not touched). Wall time and peak RSS were captured per process with `wait4`; peak RSS is reported in bytes on macOS.

| Run | Wall time | Peak RSS |
| --- | --- | --- |
| `reindex --full --search` (full-text index only) | 3.06 s | 165.7 MB |
| `reindex --full --embeddings` (embedding pass over the indexed notes) | 2.65 s | 361.9 MB |
| `reindex --full` (full-text index + embeddings) | 4.05 s | 373.7 MB |

Both embedding runs reported `20 entities embedded, 0 skipped, 0 errors` (index `sqlite-vec`, `FastEmbedEmbeddingProvider:bge-small-en-v1.5:384`). Loading the ONNX embedding model roughly doubles the process's peak memory, from about 166 MB for text indexing to about 362–374 MB with embeddings. A first attempt that ran the embedding pass against a fresh store embedded 0 entities — the embedding pass depends on the project index existing first — so the recorded embedding figure runs in the same store after the full-text index.

Text search returned all 20 notes after indexing, and the corpus hashes were unchanged before and after. Caveats: this is a 20-note corpus, so absolute cost will scale with corpus size; the measurement covers the CLI reindex process including its startup, not the in-server background indexer, though both use the same FastEmbed provider.

```sh
uv run --locked python evaluation/indexing_cost/run.py
```

## Engine configuration and compatibility

The configuration sets `HF_HUB_OFFLINE=1` to prevent embedding-model downloads. In the Codex run, FastEmbed attempted background indexing with `BAAI/bge-small-en-v1.5`, but the weights were absent; the OpenCode run downloaded them before its configuration was fixed (see the download record above). Full-text indexing and all searches succeeded in both. This does not disable background inference or establish a model-free configuration. No hosted embedding provider was configured; [indexing wall time and memory use have since been measured](#indexing-cost-measurement--14-november-2026).

Python 3.14 compatibility checks passed: `uv pip check`, CLI version/help, MCP tool registration, native ONNX Runtime/FastEmbed imports, async SQLite FTS5 create/insert/search, and SQLite vector-extension loading. These are smoke checks, not a complete upstream test suite or an embedding inference test.

## Protected eligibility probe — 16 November 2026

**Passed through the protected service:** accepted/proposed/rejected/superseded/expired/environment-inapplicable/deleted eligibility after warmed reads, both native index rebuild modes and facade restart. [Recorded result](../evaluation/phase1b/runs/20261116T113301.888339Z-real-clients/result.json), [independent evidence audit](../evaluation/phase1b/runs/20261116T113301.888339Z-real-clients/evidence-audit.json), [probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/eligibility_lifecycle.py).

Codex 0.169.0, OpenCode 2.3.0 and Claude Code 2.1.311 used the existing real-client runners against the fresh owner-provisioned fixture. All provisioning, reviewer operations, reindexing and service control ran in the owner's terminal. Reviewer operations were batched once their proposal IDs were available. The agent consumed seven service-owned artifacts, each revalidated for protected ownership and exact run, fixture and operation arguments; it never opened the protected database. A named configuration preserved the previous public evidence configuration.

Each client performed two reads of each tested path in five phases: warm baseline, first post-change reads, after `reindex --full --search`, after `reindex --full`, and after facade restart. This produced **30 retrieval turns: 60 default knowledge searches and 270 explicit gets**, plus seven seed proposals and three successor proposals. All 330 retrieval calls were independently re-parsed from the retained raw client transcripts and checked against exact arguments and expected responses.

| State | Default knowledge search | Explicit get |
| --- | --- | --- |
| Accepted control | Present in every phase | Accepted revision 1 remains readable. |
| Proposed | Absent before and after changes | Proposal remains `proposed`, with no decisions. |
| Rejected | Absent before and after rejection | Proposal is `rejected`, with its rejection decision. |
| Superseded | Old-body-only query becomes empty; accepted successor remains present in the shared query | Current revision 2 is accepted; revision 1 is superseded and its body remains available in explicit history. |
| Expired | Initially eligible; absent as soon as the past-expiry successor is accepted | Accepted revision 2 remains readable with `expired: true`. |
| Environment-inapplicable | Initially eligible; absent after acceptance changes its restriction, with caller checkout unchanged | Accepted revision 2 remains readable with `applicable: false`. |
| Deleted | Initially eligible; absent after reviewer deletion | Record ID returns `NOT_FOUND`. |

Default get was checked for every state. The history and proposals views were also warmed and repeated on the superseded record. After both index rebuilds and restart, trusted snapshots matched the post-change workflow rows and canonical note hashes exactly. Both rebuilds indexed four notes with zero failures; full rebuild skipped embeddings through the expected keyword-only fallback. All 26 live-corpus Markdown files retained their original hashes. Existing evidence and failed attempts were retained.

| Retrieval path | Cache finding | Verified coverage |
| --- | --- | --- |
| Facade knowledge search | [`Facade.knowledge_search`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/facade.py) rechecks workflow rows, current revision, expiry and environment on each native hit. `_notes` caches client objects, not results. | First post-change reads and repetitions passed in all clients and phases. |
| Native FTS search reached by `NotesClient.search` | Basic Memory 1.0.0's search route has an optional `cached_read` dependency. The protected runner observed **48 bypasses before restart and 12 after restart, with zero configured cache targets in either process**. | Actual native search-cache bypass was observed on all 60 calls. This is repeated-read eligibility evidence, not verified cache invalidation. |
| Explicit `memory_get`, history and proposals | [`Facade.get`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/facade.py) reads workflow SQLite rows through [`WorkflowStore`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/store.py); it does not call the native note-read cache. | All 270 explicit gets had the documented state behavior. No result-cache invalidation claim. |

All 14 guard files were retained: ten reviewer processes, two reindex processes and both facade boots. Their only blocked imports were expected `sqlite_vec` probes; **zero inference imports and zero outbound service connections** were attempted. Client model traffic was permitted and is outside those service guards.

The sandbox initially blocked Codex startup before any tool calls; that attempt is archived under `sandbox-denied/`. An initial retry used a relative script path that failed protected source validation before client operations. OpenCode later completed two searches in reverse order, exposing a verifier assumption: the probe now matches responses by exact arguments while retaining the original events and extracted calls under `verifier-ordering/`. Existing captures were revalidated rather than rerunning owner operations. A 30-minute full-rebuild checkpoint wait also expired before the owner's artifact arrived; the same run resumed from retained captures and the subsequently validated artifact. The retained resume/audit scripts and replay manifests document these resumptions. This is a staged probe, not an uninterrupted run or recovery test.

Regression validation: **40 distinct tests and 25 subtests passed**. The focused selection passed 24 tests and 16 subtests (`tests/workflow/test_search.py`, `tests/workflow/test_service.py`, `tests/workflow/test_facade_integration.py`, `tests/evaluation/workflow/test_real_clients.py`, `test_boundary_trust.py`, `test_eligibility_lifecycle.py`). The broader workflow/bundle selection passed 14 tests and 9 subtests in the sandbox; its two loopback-dependent facade/boundary tests initially failed at socket bind with `EPERM`, then both passed with local socket access. The nine eligibility tests passed again after correcting completion-order matching, and the evidence audit revalidated the actual reversed-order captures. Ruff and `git diff --check` passed.

**Limits:** expiry was introduced by accepting a successor with past `expires_at`; real-client wall-clock expiry crossing remains untested. There was no configured result cache on these retrieval paths, so cache invalidation with an active native cache remains untested. Explicit history/proposals view repetition was scoped to the superseded record. This probe establishes neither sustained-load, concurrency, recovery, persistent deployment nor rollout gates. No commit or push was made.

## Protected wall-clock expiry probe — 16 November 2026

**Passed through the protected service:** an unchanged accepted revision became ineligible solely because its expiry boundary passed. [Recorded result](../evaluation/phase1b/runs/20261116T175515.558471Z-real-clients/result.json), [independent raw-evidence audit](../evaluation/phase1b/runs/20261116T175515.558471Z-real-clients/independent-evidence-audit.json), [audit script](../evaluation/phase1b/runs/20261116T175515.558471Z-real-clients/audit.py), [probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/wall_clock_expiry.py). This closes E14's real-client wall-clock expiry gap, not its active-cache invalidation gap. E14 and all 278 retained artifacts remain unchanged.

Codex 0.169.0, OpenCode 2.3.0 and Claude Code 2.1.311 used E14's existing real-client runners against Basic Memory 1.0.0 in a fresh fixture. The facade's existing read-time expiry implementation was unchanged; the harness extracts E14's reusable exact-argument matcher and adds UTC turn bounds and trusted snapshot timestamps. All provisioning, acceptance, reindexing and service control ran in the owner's terminal. Both seed acceptances were batched; the post-expiry snapshot and search-only rebuild were also issued together, in that order. Rebuilds remained separate so clients could read between them. The existing protected interpreter/workflow sources were reused; only the snapshot-timestamp change was copied to the protected runner. A named configuration preserved previous public evidence configurations.

The expiring record's `expires_at` was fixed at proposal creation, 30 minutes ahead: **2026-11-16 18:27:10.504481 UTC**. It and the non-expiring control were accepted once at revision 1; there was no successor, metadata edit, deletion or canonical rewrite. Each client completed two warm turns, searching default knowledge (omitting `view`) and explicitly getting both records, between 17:58:38 and 17:59:28 UTC. The trusted warm snapshot at 18:02:31.916696 UTC matched the accepted snapshot exactly. The harness requires every warm turn and this snapshot to finish at least 120 seconds before expiry; missing the deadline fails clearly and requires a fresh fixture rather than extending stored expiry.

After waiting across the real UTC boundary, the first post-expiry turn started at **18:27:11.509282 UTC**, about one second after expiry. Each client's first search excluded the expiring record with reason `expired`; the repeated search did too. Explicit get still returned accepted revision 1 with `expired: true` and differed from its eligible baseline only in that computed flag: identity, revision, metadata, body, history and checksum were identical. The non-expiring control remained present in search and explicit get throughout.

| Phase | Default searches | Explicit gets | Outcome in all three clients |
| --- | --- | --- | --- |
| Warm | 6 | 12 | Both accepted revision-1 records eligible; explicit gets unexpired. |
| First/repeated post-expiry reads | 6 | 12 | Expiring record excluded from search; explicit get expired; control unaffected. |
| After native `reindex --full --search` | 6 | 12 | Same eligibility and explicit-get behavior. |
| After native `reindex --full` | 6 | 12 | Same eligibility and explicit-get behavior. |
| After facade restart | 6 | 12 | Same eligibility and explicit-get behavior. |

All **30 retrieval turns, 30 default searches and 60 explicit gets** passed, plus the two seed proposals. The independent audit re-parsed all 90 retrieval responses from the raw client transcripts, matched exact tool arguments rather than completion order, and checked them against the saved responses and eligible explicit-get baseline. Every warm turn finished before the deadline; every post-expiry turn started after expiry. Raw transcripts, prompts, extracted calls/responses, UTC turn bounds, trusted snapshots, owner operation outputs and guard counters are retained in the run directory.

All eight service-owned artifacts were revalidated for protected ownership and exact run, fixture and operation. After acceptance, warming, expiry, both rebuilds and restart, all workflow rows, their column definitions and canonical Markdown hashes matched exactly. In particular, the trusted post-expiry snapshot at 18:29:40.527031 UTC preceded the first rebuild and matched the warm snapshot, isolating time from any stored workflow/canonical mutation. This proves logical workflow/canonical immutability, not physical database-file immutability: derived native indexes may change during rebuilds. Both rebuilds indexed two notes with zero failures; the full rebuild skipped embeddings through the expected keyword-only fallback. All **27 live-corpus Markdown files** retained their original hashes.

All **six completed guard files** were retained: two acceptances, two rebuilds and both facade boots. Their only blocked imports were expected `sqlite_vec` fallback probes; **zero inference imports and zero outbound service connections** were attempted. Client model traffic was permitted and is outside the service guards. The first facade boot recorded 24 native search-cache bypasses and the restarted boot recorded six, with zero configured cache targets in either. Facade search/get have no result cache; this establishes **repeated-read eligibility, not active-cache invalidation**.

Regression validation: **65 tests and 25 subtests passed** across `workflow/`, `test_real_clients.py`, `test_boundary_trust.py`, `test_eligibility_lifecycle.py`, `test_wall_clock_expiry.py` and `test_workflow_integration.py`. The focused 50-test selection passed again during final client reads. New tests cover the facade at the exact expiry instant with unchanged input rows, deadline rejection, reversed completion matching, leaked expiry results, missing controls, changed explicit-get content/revisions/expiry, guard rejection, fresh-fixture enforcement, and simulated end-to-end checkpoint orchestration with workflow/canonical-mutation rejection. Simulation is not real-client evidence. All 32 retained E14 turns (30 retrieval and two proposal turns) were also re-parsed through the extracted shared matcher with identical responses, including reversed OpenCode completions, without rerunning clients or owner operations. Ruff and `git diff --check` passed. [Local preparation artifacts](../evaluation/phase1b/runs/wall-clock-preparation-20261116/) retain regression output, matcher replay audit and a preservation manifest for the live corpus and E14 evidence. The first broad regression attempt exceeded its 120-second outer timeout; the background rerun completed in 147 seconds, including the existing core, facade, reviewer-race, upgrade, disposable-boundary and trusted-artifact subprocess tests. These regressions add no new protected concurrency or recovery claim.

For another run, the owner must provision a fresh fixture/configuration and start its facade. Use the existing protected runtime and owner checkpoints, not the now-expired recorded fixture. The agent-side launch is:

```sh
PHASE1B_BOUNDARY_CONFIG=/path/to/service-home/boundary-evidence/FRESH_CONFIG.json \
  uv run --locked python evaluation/workflow/real_clients.py --protected-identity --wall-clock-expiry
```

The harness emits exact owner commands as their dependencies become available; checkpoints time out after 30 minutes. The initial owner provisioning block used a nonexistent `/usr/bin/test` and exited the interactive shell under `set -e`, before creating any fixture/configuration. It was corrected to macOS's `/bin/test` inside a subshell before provisioning. One Codex post-search-rebuild turn spanned 44 minutes 56 seconds of wall clock before completing successfully; no client or reviewer operations were replayed and no harness resumption was needed. The final snapshot at 19:28:15.545921 UTC was taken after stopping the second facade boot.

**Limits:** one time-only boundary and one non-expiring control, sequential client turns with possible parallel tool completions, no configured result cache, and logical workflow/canonical snapshots rather than physical SQLite-file immutability. This is not a latency or sustained-load test and proves no concurrency, recovery, persistent-deployment or rollout gate. No software was installed; no commit or push was made.

## Portability and recovery preparation — 16 November 2026

**Local preparation completed; the protected deployment result is recorded below.** The inventory's missing-history/importer claim was stale: [version-3 workflow bundles](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/bundle.py) already export complete workflow rows and canonical native JSON from one consistent read transaction, then import into a migrated fresh store, relocate paths, materialize notes, rebuild/validate keyword indexes and activate staging. The existing [bundle integration test](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/tests/workflow/test_bundle_integration.py) exercises restore without the original database/corpus, historical acceptance retries, observations/relationships, deleted provenance, interrupted deletion recovery, manifest/reference/checksum rejection and failed-import activation refusal. E4's OKF limitations describe the native exporter, not this workflow implementation. No production bundle or integration behavior was changed for this drill.

The [new probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/portability.py) reuses E13–E15's actual Codex/OpenCode/Claude Code runners, retained transcripts, call-ID response parsing and exact-argument matching. Its [protected operations](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/portability_service.py) seed a fresh fixture with two accepted revisions, pending and rejected edits with decisions, source metadata, supersession and deleted-parent provenance, native observations/relationships, proposal/acceptance/handover/completion/deletion receipts, active/completed/past-expiry handovers, expired and environment-inapplicable knowledge, and a foreign project's accepted record. Finalized deletion intentionally preserves revision identity tombstones without deleted content, proposals or decisions.

The transport owner batch exports a version-3 logical bundle and independently takes a consistent `sqlite3.Connection.backup` snapshot. It renames the original state/config/corpus directories out of their original locations before either restore. Logical import consumes only the bundle; database restore consumes only the backup, rebinds native paths and reconstructs canonical files from backed-up content. Both rebuild native keyword indexes with the existing integration primitive. Dedicated child processes for native migration/reindexing carry the same unavailable-inference/network guards; only expected blocked `sqlite_vec` fallback probes are permitted. This is a test-harness wrapper around existing primitives, not a new bundle format or recovery API.

Trusted snapshots compare every exported native field, complete workflow rows and canonical hashes with the source baseline. Logical external identities are preserved while numeric native IDs may be reassigned; the backup path separately checks native project/entity numeric IDs. All canonical paths must lie under the respective restored fixture. Each restored facade is identified by a trusted running-process marker before client calls; both stopped facade guards must be present at final verification. Each actual client must return eligible accepted knowledge, exclude proposals/rejected/old-body/expired/inapplicable/deleted/foreign knowledge, expose complete explicit history and proposal decisions, preserve handover content/status and exclude completed/expired handovers from active results. Codex replays proposal, handover-save and completion receipts through each restored facade and attempts changed-payload reuse. Owner-side acceptance retries return original revisions, reject changed payloads and replay deletion receipts. Snapshots after retries must remain equal to the source baseline.

Owner commands and raw service calls/results/timestamps, native subprocess stdout/stderr, bundle manifest/checksums, backup digest, trusted source/restored snapshots, client call/response/timing artifacts and service guard counters are retained. Every trusted artifact is bound to the exact probe run, source fixture and serialized operation, and revalidated at completion. The archives and native subprocess outputs remain inside the protected fixture; public trusted artifacts contain the baseline, manifest, digests and verification snapshots. The local preparation preservation manifest covers all live corpus files and existing E13–E15 evidence; these are not restore inputs.

Run [the preparation script](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/portability_owner_prepare.sh) **in the owner's terminal**:

```sh
bash evaluation/workflow/portability_owner_prepare.sh
```

It reuses the already installed protected Python environment, copies sources into a fresh protected code directory, creates a fresh fixture and publishes a uniquely named configuration. It installs no software and leaves existing runtime sources/configurations/evidence unchanged. Its subshell stops on failure. It prints the exact agent-side `real_clients.py --protected-identity --portability` command with that configuration. The probe then prints owner checkpoint commands; exports, backups, restores, reviewer actions, guarded native rebuilds and both facade boots remain in owner terminals. A separate terminal is needed for foreground facade service control.

Preservation guarantees apply to the exercised pinned Basic Memory 1.0.0 workflow contract. The logical bundle excludes native change-log partitions, semantic vector projections, note sections and temporal assertions; reconstructed keyword indexes do not prove semantic recall. Deleted bodies are intentionally unavailable. The drill tests normal consistent restore and receipt replay, not process/power-loss crash recovery, fault injection, sustained load, concurrency, cross-version migration, active-cache invalidation, persistent deployment or rollout approval. E13–E15 remain independent evidence; the protected run below supplies portability evidence within these limits.

Regression validation: **92 distinct tests and 31 subtests passed**: 74 unit tests with 22 subtests, plus 18 integration tests with nine subtests. The first integration run passed 16 tests and failed the two loopback-dependent facade/boundary tests at sandbox socket binding; both passed with local socket access (94.80 seconds). The 14-test portability/verifier selection passed, and the restored-facade integration test passed again after strengthening complete proposal/candidate/decision comparisons. These use disposable same-user fixtures and direct facade calls, not actual-client protected deployment evidence. Local validation proves separate logical/SQLite reconstruction, complete exported state/canonical preservation, rebuilt text recall, explicit history/proposal/handover access, exclusions and foreign-project denial, original receipt replay and changed-payload refusal. Guard negative controls reject inference imports, outbound connections and missing native-child/facade evidence; artifact controls reject wrong run, fixture or operation. The source database/config/canonical paths remained absent during restored reads and retries.

Repository-wide Ruff lint and all seven changed/new Python files' format checks passed, as did shell syntax and `git diff --check`. The required repository-wide format check reports three existing unformatted files (`wall_clock_expiry.py`, `test_wall_clock_expiry.py`, `tests/workflow/test_search.py`); Pyrefly reports 11 diagnostics in pre-existing code in `boundary_service.py`, `eligibility_lifecycle.py`, `real_clients.py`, `test_wall_clock_expiry.py` and `tests/workflow/test_search.py`, with none in the new portability modules/tests. These unrelated issues were left unchanged. Checks used the installed environment with `UV_NO_SYNC=1`, `UV_OFFLINE=1` and a project-local uv cache; no dependencies were installed. [Preparation artifacts](../evaluation/phase1b/runs/portability-preparation-20261116/) retain test/check outputs and the preservation manifest: **27 live-corpus files and all 710 E13–E15 artifacts unchanged**. The protected run below separately supplies actual-client deployment evidence.

## Protected portability and recovery probe — 16 November 2026

**Passed through the protected service:** separate version-3 logical export/import and consistent SQLite backup/restore preserve the complete supported workflow contract, with eligible recall and historical access through Codex, OpenCode and Claude Code on each restored facade. [Recorded result](../evaluation/phase1b/runs/20261116T195353.081729Z-real-clients/result.json), [independent evidence audit](../evaluation/phase1b/runs/20261116T195353.081729Z-real-clients/independent-evidence-audit.json), [raw-audit script](../evaluation/phase1b/runs/20261116T195353.081729Z-real-clients/audit.py), [probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/portability.py). This supplies the missing protected portability evidence; it is not crash recovery or rollout approval.

The owner provisioned a fresh fixture using the already installed protected CPython 3.12.16 environment and a fresh protected source copy. Basic Memory 1.0.0, Codex 0.169.0, OpenCode 2.3.0 and Claude Code 2.1.311 were used. All provisioning, fixture/reviewer operations, export, backup, restore, native migration/index rebuilds and service control ran in owner terminals. Setup/configuration, fixture/export/restore, service switches and final retries/snapshots were batched in failure-stopping subshells where dependencies permitted. No software was installed, and no commit or push was made. The existing version-3 bundle implementation and native integration were reused unchanged.

The source fixture contained five surviving records, six immutable revisions, eight surviving proposals, seven surviving review decisions, three handovers, 22 retry receipts and one deleted-revision tombstone across two projects. Its native canonical state contained five notes, one observation and one relationship. Nine proposals, seven acceptances, rejection, deletion, three handover saves and completion were seeded through the actual service core by the trusted owner; complete call arguments/results and UTC bounds are retained in the trusted seed artifact. Deletion intentionally removed the parent's content/proposal/decision while preserving its identity tombstone and the child's provenance reference. This does not claim preservation of data intentionally deleted under the existing contract.

The owner exported a logical JSON bundle and independently used SQLite's consistent backup API. Before either restore, the original database/config and both canonical directories were renamed out of their original paths; those paths remained absent throughout restored reads and retries. Logical import consumed the version-3 bundle into a fresh migrated database, preserved stable external identities, reassigned numeric native IDs and rebuilt keyword indexes. Database restore consumed the independent backup, preserved native project/entity numeric IDs, rebound native paths, reconstructed canonical files from backed-up content and rebuilt indexes. Both restored native project paths point inside their own restored fixture; neither service depends on the original absolute project paths, canonical files or source database. The source remains quarantined, not destroyed. The trusted transport artifact retains the bundle manifest, archive/backup digests and all three guarded native subprocess operations with stdout/stderr and timestamps. The audit independently recomputed every manifest-entry checksum from the trusted source's native/workflow rows.

Every exported native field, all workflow rows and all canonical hashes matched the trusted source immediately after each restore, at the service checkpoints, after receipt retries and in the final snapshot at **20:05:53 UTC**. This preserves complete non-deleted historical bodies, metadata, identities, provenance/supersession, native observations/relationships, pending and rejected proposals, reviewer decisions, active/completed/expired handovers, expired and environment-inapplicable knowledge, deletion tombstones and receipts. Each restore replayed seven acceptance receipts, including original revision 1 after supersession and acceptance of the later-deleted parent, rejected changed acceptance payloads, and replayed the finalized deletion receipt. These operations left native/workflow state and canonical bytes unchanged.

All three actual clients independently exercised each restored facade. **Eight successful turns produced 92 calls:** 18 searches (12 default knowledge searches and six active-handover searches), 66 explicit gets, four proposal calls, two handover-save calls and two completion calls. Default recall returned only the accepted successor and accepted child; old-body-only queries were empty. Proposed, rejected, superseded-body, expired, environment-inapplicable, deleted and foreign-project knowledge remained excluded. Active handovers were unreviewed; completed/expired handovers were absent from the active view. Explicit gets exposed complete revision history, full candidate content and decisions for pending/rejected proposals, and complete handover metadata/status; deleted records returned `NOT_FOUND`, and foreign-project IDs returned `PROJECT_MISMATCH`. Codex replayed proposal/save/completion receipts through both facades and received `PAYLOAD_REUSE` for changed proposal payloads. Responses were matched by call ID or exact arguments, then re-parsed independently from raw transcripts. The two restores returned identical explicit content/metadata to all clients.

The owner accidentally stopped the database facade after its retrieval turns and before its retry turn completed. The original failed capture and four transport errors remain retained in `failure.json` and `codex-database-retries*`; they are excluded from the successful-call count. A read-only health check confirmed connection refusal, and the owner confirmed the accidental stop. The [continuation](../evaluation/phase1b/runs/20261116T195353.081729Z-real-clients/resume.py) revalidated the existing raw evidence and trusted artifacts, required a new trusted database-service checkpoint, and replayed only the interrupted four-call retry turn under a new capture name. The subsequent owner acceptance/deletion replays and final snapshot passed. This is a recorded service-stop/harness continuation, not a crash-recovery experiment. The continuation's module initialization created the otherwise unused directory `20261116T200322.323161Z-real-clients`; successful resumed evidence remains attached to the original run.

All **nine trusted artifacts** were revalidated for protected ownership and exact run, source fixture and operation arguments. The final trusted snapshot retains **14 completed guards**, including the three native migration/reindex subprocesses, logical facade boot and both database facade boots: only expected blocked `sqlite_vec` fallback probes, **zero inference imports and zero outbound service connections**. The logical and first database boots each recorded six native search-cache bypasses with no configured cache target; the resumed boot handled only receipt calls and recorded zero searches. The final snapshot process also writes its own guard privately on exit. Client model traffic is outside the service guards. The independent audit confirms **all 27 live-corpus files and all 710 E13–E15 artifacts unchanged**. Raw calls/results, prompts, transcripts, exit codes, UTC turn bounds, manifest/digests, trusted snapshots, native outputs, owner scripts and guard counters are retained; archive and backup bytes remain protected in the fixture.

Regression results remain **92 tests and 31 subtests passed**, with the repository-wide pre-existing formatting/type-check limits recorded in the preparation section. This proves normal consistent logical portability and database restore for the exercised pinned contract. Logical bundles intentionally exclude native journal partitions, vectors, note sections and temporal assertions; deleted bodies are absent by contract. Cross-version migration, semantic recall, active-cache invalidation, process/power-loss crash recovery, sustained load, concurrency, persistent deployment and rollout approval remain unproven.


## Concurrency and bounded-load preparation — 16 November 2026

**Preparation status before execution: protected execution was pending; no protected concurrency or load result was claimed.** E10 supplies functional independent-reviewer races in a disposable store. E13 establishes protected real-client workflows; E14–E15 establish repeated-read/rebuilt-index/restart eligibility and time-only expiry; E16 establishes protected normal restore. Those runs do not supply synchronized protected reviewer races or overlapping three-client load.

The [owner operations](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/concurrency_service.py) reuse the existing reviewer entry point, service/store transactions, native acceptance hook, checksum CAS and retry ledger. Two independent processes synchronize after capturing the original proposal base and before native writes for competing edits, creates at the same project/path, identical-key acceptance and changed-payload acceptance-key reuse. Three further pairs synchronize before the handover transaction for update/update, update/completion and completion/completion with expected revision 1. Fresh-process retries preserve outcomes. The checks require one committed transition (identical duplicate acceptance returns two equal receipts for one commit), pending losing proposals without decisions or independent acceptance receipts, no losing new record or canonical file, and no extra revisions/decisions/receipts. Trusted snapshots validate database integrity, foreign keys, revision bodies, native/workflow checksums and an exact canonical path/hash map. Complete before/after snapshots and worker arguments/results/PIDs/UIDs/UTC barrier bounds are retained.

The fixed [workload definition](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/concurrency_workload.py) precedes execution: **two waves, three simultaneous actual-client turns per wave, ten calls per turn, 60 calls total; each wave has a 1,200-second deadline, with no automatic extension or replay.** Each client captures/retries a pending proposal, rejects changed-payload reuse, recalls the accepted main-project control, denies a foreign-project get, updates/retries its own seeded handover, rejects a stale update, and reads active unreviewed handovers. A fixture-only server barrier holds the first capture, recall and handover requests from different clients until all three arrive (120-second maximum); its wait is separately measured. This deliberately synchronized request overlap is distinct from simultaneous handler execution or production traffic. No latency/throughput acceptance threshold is being inferred from results.

The [actual-client harness](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/concurrency_load.py) reuses E13–E16's Codex, OpenCode and Claude Code runners and exact-argument/call-ID response matching. Wave orchestration uses `asyncio.Barrier` and `asyncio.gather`, with existing blocking client runners dispatched through `asyncio.to_thread`, following the owner's preference. The first pending run (`20261116T203332.231605Z-real-clients`) was stopped at its initial owner checkpoint to apply that change; it made no client or owner operation calls, and its workload/preservation/failure artifacts are retained. The asyncio revision passed the 15 isolated verifier tests and the focused race/60-call transport/orchestration integration; static-check diagnostics remain unchanged. Pass criteria require all six turns and exact responses within the predefined bounds, mixed request overlap in both waves, equal duplicate receipts, six expected payload-reuse denials, six stale-handover conflicts and six foreign-project denials, and no unexpected errors. Native state/canonical hashes remain unchanged during load; only six pending proposals, six proposal receipts, six handover-update receipts and the three handovers' intended fields/revisions may change. Trusted artifacts are revalidated for protected ownership and exact run/fixture/serialized operation; every worker and service guard must be present. Expected blocked `sqlite_vec` fallback is permitted; inference imports and outbound service connections fail verification.

Measurements retain raw client prompts/transcripts/calls/responses, turn UTC bounds, all service request/response events with monotonic bounds, gate wait and handler execution time, per-tool latency distributions, calls/second over measured wave time, expected/unexpected errors/conflicts, facade CPU/peak RSS and one-second client process-tree RSS/CPU samples. Turn latency includes client startup, model, transport and service time; model latency is not separately observable. Service timing excludes transport and separately removes the artificial gate wait. Facade resource totals include owner/checkpoint idle time; `ps` CPU percentages are lifetime averages, and sampled RSS is not a true peak allocation measurement.

Local preparation exposed native `note_content.updated_at` bookkeeping changes on stale acceptance retries, with all other exported native fields, workflow rows and canonical bytes unchanged. Basic Memory's `NoteContent.updated_at` has an `onupdate` default (`basic_memory/models/knowledge.py`); sync-field updates use it (`repository/note_content_repository.py`). The race verifier retains both raw native snapshots, reports any such timestamp differences explicitly and compares every other native field exactly. Load itself still requires exact native equality. This is not a new revision or changed accepted body.

[Preparation artifacts](../evaluation/phase1b/runs/concurrency-preparation-20261116/) retain local regression/check output, disposable fixture evidence and a preservation manifest for the live corpus and E10/E13–E16 evidence. The 15 new isolated verifier tests passed; the focused local integration passed all seven race cases plus fresh-process retries, 60 HTTP MCP calls and final state/guard validation. That integration uses direct MCP test clients, not the three model clients or service account. The full regression passed **108 tests: 89 isolated tests and 19 integration tests**, with the integration suite completing in 203.83 seconds. The new integration also replays the retained local transport captures through the complete orchestration/verifier. Repository-wide Ruff lint passed; changed/new files' format checks, shell syntax and `git diff --check` passed. The repository-wide format check still reports the three pre-existing files documented in E16, and Pyrefly still reports the same 11 pre-existing diagnostics, with none in the new concurrency modules/tests. Checks used the installed environment with `UV_NO_SYNC=1`, `UV_OFFLINE=1` and a project-local uv cache. All **27 live-corpus files and 858 E10/E13–E16 artifacts** match their preservation manifest. The initial sandboxed attempt was refused at loopback bind; the transport regression used permitted loopback access. A test teardown initially used SIGTERM, which bypassed final resource capture; normal Ctrl-C shutdown now matches the planned owner-terminal procedure. Failed preparation artifacts remain retained.

Provisioning uses [the owner preparation script](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/concurrency_owner_prepare.sh), a fresh protected code copy and fixture, the existing protected interpreter, and a new named configuration on port 8768. Preparation and foreground service start are batched in a failure-stopping owner subshell. Reviewer operations, provisioning and service control remain in owner terminals; no software installation, commit or push is part of this probe. This bounded result will remain separate from sustained production capacity, persistent deployment, active-cache behavior, crash recovery, the everyday-use trial and rollout approval.

## Protected concurrency and first bounded-load attempt — 16 November 2026

**The seven protected reviewer/handover race cases passed; the first bounded client workload failed its exact-argument criterion.** [Trusted preparation capture](../evaluation/phase1b/runs/20261116T203517.944553Z-real-clients/prepare-concurrency.json), [fixed original workload](../evaluation/phase1b/runs/20261116T203517.944553Z-real-clients/workload.json), [retained failure](../evaluation/phase1b/runs/20261116T203517.944553Z-real-clients/failure.json), [independent audit script](../evaluation/phase1b/runs/20261116T203517.944553Z-real-clients/audit.py). The owner provisioned a fresh fixture with protected CPython 3.12.16 and Basic Memory 1.0.0; preparation and foreground service startup ran in the owner's terminal, followed by a trusted readiness snapshot in a second owner terminal.

Independent protected reviewer processes produced exactly one committed edit successor, one winner for the colliding new path, one committed receipt for duplicate same-key acceptance (two identical successful results), and one winner with changed-payload key reuse rejected. Losing proposals remained pending without decisions or independent acceptance receipts; the losing new target IDs never became records. Handover update/update, update/completion and completion/completion pairs each committed one revision-2 outcome and rejected the other. All seven cases were replayed by fresh process pairs with unchanged outcomes and workflow/canonical state. Per-process UIDs/PIDs, barrier bounds, native write inputs, complete responses and snapshots are retained in the trusted preparation artifact. Database integrity and foreign-key checks passed.

The three actual clients started wave zero together. Codex, OpenCode and Claude Code each completed ten tool calls. Claude's foreign-project `memory_get` sent a checkout commit containing **42** `d` characters instead of the specified **40**; the service still returned the expected `PROJECT_MISMATCH`. The strict exact-argument matcher rejected that call, correctly failing the workload after 29 exact matches and one mismatch. Wave one never started, and no operation was replayed. All raw outputs and timings remain retained. This is a client argument-fidelity failure, not evidence of a service transaction failure; it is not reported as a passing bounded-load run. The [independent audit](../evaluation/phase1b/runs/20261116T203517.944553Z-real-clients/independent-evidence-audit.json) subsequently revalidated all three trusted artifacts and all 30 raw client/service responses after the owner's normal stop. Exact native state and canonical hashes matched the prepared baseline; only the intended three pending proposals, six receipts and three revision-2 handovers changed. Database integrity/reference checks passed; all 31 completed guards allowed only blocked `sqlite_vec` fallback probes, with zero inference imports and zero outbound service connections. All 27 live-corpus files and 858 E10/E13–E16 artifacts remained unchanged. The observed first-wave client interval was 39.888044 seconds; service handler latency after the fixture gate was median 1.201 ms, p95 39.321 ms and maximum 43.449 ms. These partial-attempt measurements are excluded from the fresh attempt's results, and the first workload remains failed.

A **fresh** second attempt used workload version 2: the fixture commit became the shorter `d1e2f3a4b5c6`. The two-wave/three-client/60-call definition, 1,200-second wave deadlines, 120-second fixture gate and all pass criteria were unchanged. The failed attempt is retained separately; there was no relaxed argument matcher, automatic operation replay or retrospectively chosen rollout threshold. The changed fixture value passed the 15 isolated verifier tests and the focused synchronized-race/60-call/asyncio-orchestration regression. The second attempt used a new protected source copy, fixture and configuration; no live corpus or earlier evidence was its input. Its result follows.

## Protected concurrency and bounded multi-client load — 17 November 2026

**Passed: all seven synchronized protected race cases and the predefined two-wave, three-client workload.** [Recorded result](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/result.json), [independent raw-evidence audit](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/independent-evidence-audit.json), [audit script](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/audit.py), [workload recorded before execution](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/workload.json). This supplies protected-deployment concurrency evidence beyond E10's functional disposable-store races and bounded overlapping load beyond E13–E16's protected workflows. It establishes neither sustained production capacity nor rollout approval.

The owner provisioned a fresh fixture using the existing protected CPython 3.12.16 environment, Basic Memory 1.0.0 and a fresh protected source copy. Codex 0.169.0, OpenCode 2.3.0 and Claude Code 2.1.311 used their existing real-client runners and logins. Workflow/service/store acceptance, retry and handover behavior was unchanged; the harness adds process barriers, trusted snapshots and guarded MCP timing. Orchestration uses asyncio with the existing blocking runners dispatched through `asyncio.to_thread`. All provisioning, reviewer operations and service control ran in owner terminals; no native reindexing was needed in this probe. No software was installed, and no commit or push was made.

The [trusted preparation artifact](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/prepare-concurrency.json) retains seven synchronized process pairs and seven fresh-process retry pairs: **28 independent workers under UID 502 (service account)**, using the same protected database. Acceptance barriers occur after each process captures its proposal's stored base and before the native write; handover barriers occur before each process enters the existing `BEGIN IMMEDIATE` transaction, with both observing revision 1. PIDs, UIDs, UTC barrier bounds, write arguments, operation outputs and before/after snapshots are retained.

| Race | Observed committed outcome | Losing/duplicate outcome |
| --- | --- | --- |
| Two edits from revision 1 | Exactly one revision 2, one decision and one acceptance receipt. | `REVISION_CONFLICT`; original proposal remains pending without a decision or acceptance receipt. |
| Two new targets at the same project/path | Exactly one native note, workflow record and revision 1. | `ALREADY_EXISTS`; pending proposal, no losing record, revision, decision, receipt or canonical file. |
| Concurrent acceptance with the same key and payload | One revision, decision and receipt. | Both processes receive the identical original result, including record/proposal IDs, revision and checksum. |
| Concurrent acceptance with one key and different payloads | Exactly one accepted target and receipt. | `ReuseWithChangedPayloadError`; the other proposal remains pending with no accepted target or decision. |
| Handover update/update, expected revision 1 | One update to revision 2. | `StaleHandoverRevisionError`; no losing receipt. |
| Handover update/completion, expected revision 1 | Completion won, yielding completed revision 2. | Update receives `InvalidHandoverStateError`; no losing receipt. |
| Handover completion/completion, expected revision 1 | One completion to revision 2. | `InvalidHandoverStateError`; no losing receipt. |

Fresh-process retries returned the same outcomes without adding workflow rows or changing canonical bytes. One stale edit retry changed only native `note_content.updated_at` bookkeeping, from `2026-11-17 04:21:15.456736` to `04:21:17.944793` in the native export; both raw snapshots and the difference are retained. Every other exported native field matched exactly. This is the native sync-field `onupdate` behavior documented in preparation, not a revision or content change. Snapshot validation checked SQLite integrity and foreign keys, complete workflow history, proposal/decision/receipt relationships, native checksums and an exact canonical path/hash map. No losing canonical files or stray revisions, decisions or receipts survived.

The owner-readiness wait expired before the readiness artifact arrived, **before any client call**. The [continuation](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/resume.py) revalidated the exact preparation/readiness artifacts and unchanged client versions, then started client operations for the first time. [Resume provenance](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/resume-manifest.json) retains the original timeout and the otherwise unused initialization directory `20261117T055437.433769Z-real-clients`. No owner or client operation was replayed. Both measured waves then ran without interruption; the owner wait is outside their predefined measurement window. This continuation is not crash-recovery evidence.

The fixed workload was **two waves, three concurrent turns per wave, ten calls per turn**, with a 1,200-second deadline per wave and no automatic replay or extension. Each client proposed/retried a distinct pending capture, attempted changed-payload reuse, recalled the accepted control, attempted a foreign-project get, updated/retried its own handover, attempted a stale update and read active unreviewed handovers. The six captures remained pending; acceptance was exercised by the separate owner-run race fixtures. Exactly **60 calls** completed: 18 proposal calls, 12 searches, 12 explicit gets and 18 handover-save calls. There were **42 successful responses and 18 expected denials/conflicts**: six `PAYLOAD_REUSE`, six `STALE_REVISION` and six `PROJECT_MISMATCH`. There were **zero unexpected errors** and no extra calls. The failed first attempt's 30 calls are not included.

| Client turn wall time (seconds) | Wave 0 | Wave 1 |
| --- | ---: | ---: |
| Codex | 20.675 | 31.711 |
| OpenCode | 45.872 | 50.092 |
| Claude Code | 35.033 | 46.423 |
| Complete wave | 45.878 | 50.093 |

Measured wave time totaled **95.970697 seconds**: **0.6252 completed calls/second**, including expected denials, or **0.4376 successful responses/second**. These are end-to-end rates for this workload, including client startup/model/transport time, not isolated service throughput or a saturation limit. Client turn median was 40.453 seconds; maximum was 50.092 seconds. Model latency is not separately observable, and subtracting handler time does not isolate it.

| Service timing path | Samples | Median | p95 (nearest rank) | Maximum |
| --- | ---: | ---: | ---: | ---: |
| MCP handler interval after fixture gate, milliseconds | 60 | 1.244 | 36.235 | 81.723 |
| MCP middleware interval including gate, milliseconds | 60 | 1.279 | 12,135.222 | 24,627.370 |
| Artificial gate wait, milliseconds | 6 | 12,701.082 | 24,623.825 | 24,623.825 |

Service timing spans middleware entry to completion and excludes network transport; handler intervals include awaits and exclude the artificial synchronization wait. Per-tool distributions and every raw interval are retained in the result and trusted final capture. The fixture gate deliberately aligned capture, recall and handover requests from different clients. [Interval analysis](../evaluation/phase1b/runs/20261117T031847.700026Z-real-clients/concurrency-observation.json) observed a peak of **three in-flight requests and three handler intervals after the gate**. All three mixed handler intervals overlapped by **4.353 ms in wave 0 and 1.930 ms in wave 1**, including awaits; this is not parallel CPU execution. These small samples and synchronization do not establish ordinary production arrival behavior. No latency or throughput rollout threshold was chosen before or after seeing these results.

The facade recorded **9.182 user CPU seconds, 1.659 system CPU seconds and 206.547 MiB peak RSS**. Its resource window was 03:21:46–05:56:53 UTC, including the long owner/checkpoint idle interval and service startup; those totals are not attributed exclusively to the 95.97-second load window. The agent-side sampler retained **91 process-tree samples**, with peak sampled summed RSS **1.558 GiB** for the probe and descendant client/server processes. Summed process RSS may count shared pages more than once, sampling can miss peaks, and recorded `ps` CPU percentages are lifetime averages rather than interval CPU. No host-capacity extrapolation is made.

The final trusted snapshot at **05:56:59 UTC** preserved all exported native state and canonical hashes exactly from preparation through readiness and load. Only the intended six pending proposals, six proposal receipts, six handover-update receipts and the three clients' handover fields/revisions changed; each handover reached active revision 3. Totals were six records, seven immutable revisions, 16 proposals, seven decisions, six handovers and 38 retry receipts across two projects, with six canonical notes. Accepted records, history, reviewer decisions, the foreign project and all unrelated handovers remained unchanged. Every duplicate receipt matched both the client response and stored operation result; no stale/reuse/foreign denial added a receipt. Default recall returned exactly the accepted main control; captures and handovers never became accepted knowledge.

All **three trusted artifacts** were revalidated at their original protected paths for service ownership and exact run, fixture and serialized operation. The independent audit re-parsed every raw client transcript by call ID or exact arguments, compared all 60 responses with the trusted service events, checked receipts/state and recomputed latency, overlap, throughput and sampled-memory results. All **31 completed guards** were present, including every reviewer worker and the measured facade: only expected blocked `sqlite_vec` fallback probes, **zero inference imports and zero outbound service connections**. Client model traffic remains outside those service guards. Native search observed six cache bypasses and zero configured targets, so this adds no active-cache evidence. All **27 live-corpus files and 858 E10/E13–E16 artifacts** retained their original hashes.

Final regression/check output is retained with the [preparation artifacts](../evaluation/phase1b/runs/concurrency-preparation-20261116/): **108 tests passed on the final sources (89 isolated and 19 integration)**; the integration suite completed in 198.96 seconds. The focused version-2 regression also passed all seven race cases, 60 direct MCP calls and complete asyncio orchestration/verifier replay. Repository-wide Ruff lint, changed/new Python format checks, shell syntax and `git diff --check` passed. The full format check still reports three pre-existing unformatted files (`wall_clock_expiry.py`, `test_wall_clock_expiry.py`, `tests/workflow/test_search.py`); Pyrefly still reports 11 pre-existing diagnostics with none in the new concurrency modules/tests. These unrelated issues were left unchanged. Checks used `UV_NO_SYNC=1`, `UV_OFFLINE=1` and a project-local uv cache without installing dependencies. This result covers the exercised pinned, single-host protected deployment and bounded traffic only. Persistent deployment, active-cache invalidation, crash recovery, sustained production load, the everyday-use trial, team authorization and rollout approval remain separate. E16 remains the independent normal-restore evidence; nothing here expands it into a crash-recovery claim.
