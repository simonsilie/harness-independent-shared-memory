# Fate of the custom workflow code

Decided on 18 November 2026 from the [scope reconciliation](scope-reconciliation.md) and the completed productive checks. The initial classification changed no code. The explicit retirement follow-up now preserves the complete implementation at a pinned commit and removes historical-only packages, probes and tests from the active tree. [ADR 0001](../adr/0001-personal-use-and-gap-driven-development.md) permits custom code only for a demonstrated gap against an agreed personal-use requirement; the former team and protected-reviewer contract does not qualify.

## Outcome

No `workflow/` component fills a demonstrated current requirement gap. All modules are **archived historical implementation**, removed from the active source tree together with their historical-only importers. Productive use relies on native Basic Memory tools with shared client instructions: [scoped recall](native-memory-coverage.md), [shared defaults](../personal-defaults.md), [temporary context](temporary-context.md), [actual-client conditional writes](native-client-writes.md), [backup](../productive-backup.md) and [portable export](../portable-export.md).

A reproducible shortfall in a requirement row of the reconciliation table could still justify a focused adapter; consulting an archived module would then be a design choice, not a reason to restore the package wholesale. Team infrastructure, protected reviewer deployment, a standalone ticket system and multi-computer synchronization remain outside scope under the ADRs.

## Component decisions at the archived revision

The table records the original classification and import relationships at the
[archived source revision](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61).
“Retained historical” below means retained in that archive, not in the active tree.

| Component | Former role | Why no current gap | Decision |
| --- | --- | --- | --- |
| `workflow/facade.py` | Token-authenticated streamable-HTTP MCP facade with project/checkout registry, environment eligibility and five `memory_*` tools. | Ordinary recall is native `bm_search`/`bm_read` with explicit scopes and client-side project rules; approval and outage behavior are shared client conventions ([client connections](../client-connections.md), [ADR 0002](../adr/0002-agent-proposals-with-human-approval.md), [ADR 0005](../adr/0005-proactive-recall-with-graceful-outages.md)). The facade accepts only notes backed by `wf_*` rows, so it cannot serve the productive store at all. | Retained historical. Imported by `tests/workflow/test_facade_integration.py`, `tests/workflow/test_search.py` and historical `evaluation/workflow/` probes. |
| `workflow/service.py` | Immutable proposals, accepted revisions, decisions, handovers, retry receipts and the acceptance hook's transaction boundary. | Chat approval followed by a native conditional write satisfies [ADR 0002](../adr/0002-agent-proposals-with-human-approval.md) and [ADR 0008](../adr/0008-concurrent-sessions-with-conflict-detection.md); the lifecycle is a verified client convention ([temporary context](temporary-context.md)). The immutable review ledger and retry receipts solve the superseded stronger contract; full proposal history is not an export requirement. | Retained historical. Imported by `tests/workflow/test_service.py`, `workflow/reviewer.py` and historical probes. |
| `workflow/store.py` | `wf_*` SQLite schema, migrations, canonical JSON/hash helpers and row access inside Basic Memory's database. | Productive notes live in native tables and carry their own frontmatter provenance; no workflow row is needed for recall, lifecycle or export ([native coverage](native-memory-coverage.md), [personal defaults](../personal-defaults.md)). | Retained historical; meaningful only together with the service. Imported by workflow modules and historical probes/tests. |
| `workflow/notes.py` | In-process Basic Memory API adapter for accepted writes, searches and base-revision CAS. | The actual Codex/OpenCode path already uses native `bm_write`/`bm_edit` with `expected_checksum`; stale writes conflict and preserve the winner ([native client writes](native-client-writes.md)). | Retained historical. Imported by `service.py`, `reviewer.py` and tests; no adapter in the productive client connection. |
| `workflow/integration.py` | Process-wide `on_accepted_mutation` hook, direct reads/writes of native SQLite tables and subprocess isolation for migrations and bundle restore. | Productive backup takes a consistent SQLite snapshot of the native store and its project trees ([productive backup](../productive-backup.md)); export uses native OKF commands ([portable export](../portable-export.md)). None needs the process-wide hook, internal schema coupling or Basic Memory 1.0.0 pin, which are a maintenance cost ([repository architecture](../repository-architecture.md)). | Retained historical. Used by `service.py`, `bundle.py` and historical probes. |
| `workflow/reviewer.py` | Trusted reviewer CLI for acceptance, rejection, deletion and pending proposals; its protected OS-identity boundary was enforced by the evaluation harnesses, not the module itself. | A separate approval service or protected reviewer boundary is explicitly outside scope; the owner approves in chat and the client writes the presented content ([ADR 0002](../adr/0002-agent-proposals-with-human-approval.md), [scope reconciliation](scope-reconciliation.md#what-no-longer-governs-implementation)). | Retained historical; not provisioned or invoked in productive use. Imported by historical `evaluation/workflow/` probes (`facade_guard.py`, `concurrency_service.py`, `reviewer_races.py`, `boundary_service.py`). |
| `workflow/bundle.py` | Version 3 logical ZIP bundle of canonical native state and every `wf_*` table, with a pin on one Basic Memory version. | Readable complete content with project associations, active handovers and archive is covered by per-project native OKF v0.2 bundles ([portable export](../portable-export.md)); same-version restoration is covered by the snapshot procedure ([productive backup](../productive-backup.md)). ADR 0009 does not require full revision history. | Retained historical. Imported by `tests/workflow/test_bundle_integration.py` and `evaluation/workflow/portability_service.py`. |
| `workflow/__init__.py` | Convenience re-exports of `WorkflowService` and `WorkflowStore`. | No productive entry point uses the package. | Retained with the package. |

## Retirement and retained native checks

The last complete reproducible tree is commit
`fe09180fac127bcaf48c87fc29b3577c49300e61`. No branch or tag
references it, so fetch it by SHA. Before retirement, that exact
tree passed 94 isolated tests and 37 integration tests, plus Ruff lint/format
and Pyrefly checks in the existing local Python 3.14 environment. These are local
results, not a claim that protected owner-terminal probes were rerun or that
Linux CI was revalidated.

The dependency audit separated the following files before deleting the historical
packages:

| Retained path | Actual use without the custom workflow |
| --- | --- |
| `evaluation/native/mcp_watcher.py` and `mcp_server_guard.py` | `build/semantic_runtime.py` invokes the watcher to verify model-free runtime builds; the guard blocks inference/network access in native subprocesses. |
| `evaluation/native/native_client_writes.py` | Native Codex/OpenCode checksum-conflict verification documented in [native client writes](native-client-writes.md); uses the guard, not a facade or reviewer. |
| `evaluation/native/native_memory_coverage.py` | Native scoped recall, lifecycle metadata, conditional restore and OKF export assessment documented in [native coverage](native-memory-coverage.md); uses the guard, not `wf_*` tables. |
| `tests/evaluation/native/test_semantic_disable.py` | Patch/configuration/provider-path regression coverage for pristine and already-patched Basic Memory sources. |
| `tests/evaluation/native/test_semantic_runtime_build.py` | Reproducible patched-wheel build and manifest-hash validation. |
| `tests/evaluation/native/test_mcp_watcher_integration.py` | Executes the retained model-free MCP/watcher/restart check against an isolated package copy; no installation or productive-store access. |

Everything in `workflow/`, `tests/workflow/` and the remaining historical-only
`evaluation/workflow/` probes and tests is now archive-only. This includes the
native prerequisite `run.py`/`native_cli.py` pair: it instruments the former
transaction-hook/history contract and has no active build or test consumer.
No compatibility package, acceptance hook or `wf_*` schema remains active.

Raw run directories, protected service-owned snapshots, the curated corpus,
questions, preparation pin and historical recall results remain unchanged.
Source links in historical reports point to the archived commit; historical
commands apply only in that tree. Existing `evaluation/phase1b/runs/` and
`evaluation/workflow/runs/` evidence paths are not relocated or added to Git.
Any source paths embedded in immutable corpus notes refer to that historical
tree, not an active deployment.

Retirement verification in the existing local Python 3.14 environment passed
18 isolated tests (26 subtests), 19 integration tests, Ruff lint/format, Pyrefly
and `git diff --check`. The integration suite includes the retained model-free
MCP/watcher/restart probe. All 64 historical source links in the evaluation
report, capability inventory and scope reconciliation were checked against
the archived tree; their surrounding evidence text is unchanged. No active
Python source imports the retired packages. Corpus, questions, answer key,
preparation/source pins and dependency files are unchanged.

## Historical reproduction

Browse the complete [workflow package](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow),
[probes](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow)
and [tests](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61/tests).
To run them, use a separate checkout at the exact commit above, not
the productive checkout or store:

```sh
git fetch origin fe09180fac127bcaf48c87fc29b3577c49300e61
git worktree add --detach ../shared-memory-workflow-history fe09180fac127bcaf48c87fc29b3577c49300e61
cd ../shared-memory-workflow-history
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyrefly check
uv run --locked pytest -m "not integration"
uv run --locked pytest -m integration
```

Environment creation installs the locked dependencies; the commands are
instructions, not an installation performed by retirement. The archived
[patch notes](https://github.com/simonsilie/harness-independent-shared-memory/blob/4fae58dfca94af60a602c7a69b24a7590d5b7d4c/patches/README.md)
record optional model-free patch/build setup. Historical
actual-client and protected-identity probes additionally need their documented
client credentials and owner-provisioned fixtures; the commit contains their source
and tests, not ignored raw artifacts or a provisioned OS identity.
