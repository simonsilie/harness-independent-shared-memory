# Repository architecture

The [scope reconciliation](archive/scope-reconciliation.md) distinguishes current requirements from the former workflow contract. The [custom-code decision](archive/custom-code-decision.md) records the historical implementation's retirement and the retained native checks.

The repository uses a flat Python layout with separate runtime, evaluation and
test packages. Package names describe responsibilities; phase names belong only
to historical plans and evidence.

```text
ops/                         native backup, restore and portable export
build/semantic_runtime.py    pinned model-free runtime build and verification
approval_gate/               stdio MCP proxy and owner approval CLI
evaluation/
  bm                         experiment-only Basic Memory launcher
  corpus/                    reviewed experiment notes
  questions.json            recall question set
  scoring/                   evaluator-only answer key
  recall/                    corpus preparation and retrieval scoring
  native/                    native MCP/watcher, conditional-write and coverage probes
  claude/, codex/, opencode/  client runners, inventory checks and verifiers
  clients/                   cross-client behavior and lifecycle probes
  indexing_cost/             indexing measurements
  recovery/                  recovery probes
  evidence/                  evidence collection
  observations.md            historical everyday-use observation log
tests/
  approval_gate/             proposal, proxy and native approval tests
  ops/                       recovery and portable-export integration tests
  evaluation/                harness unit and integration tests
patches/                     patches for the pinned Basic Memory dependency
docs/                        setup, architecture, ADRs and recorded evidence
```

Run commands from the repository root with uv. For scoring, set
`RUN_DIRECTORY` to a verified recall run.

```sh
uv run --locked python -m evaluation.recall.score "$RUN_DIRECTORY/results.json"
uv run --locked python -m evaluation.opencode.run --verify-only
uv run --locked memory-ops --help
WATCHFILES_FORCE_POLLING=true uv run --locked python evaluation/native/mcp_watcher.py --semantic-disabled
uv run --locked pytest -m "not integration"
uv run --locked pytest -m integration
```

Initialize the isolated experiment configuration with
`./evaluation/bm project list --local` before running the indexing-cost or
document recovery probes. The client setup guides describe the separate
evaluation configurations under each client's directory.

Corpus regeneration is an explicit authoring action, using
`uv run --locked python -m evaluation.recall.prepare`; it is not part of setup or testing against
the live corpus. The existing source-revision guard still applies.

The native checks formerly mixed into `evaluation/workflow/` now live in
`evaluation/native/`. Their legacy environment-variable names remain compatible with
the runtime build and existing invocation environments. Existing ignored
`evaluation/phase1b/runs/` and `evaluation/workflow/runs/` directories remain at
their original paths; new native runs use `evaluation/native/runs/`.
The former `evaluation/indexing-cost/` is `evaluation/indexing_cost/`, and the
root-level `prepare.py` and `score.py` are in `evaluation/recall/`.
OpenCode's startup verifier is `evaluation/opencode/verify_startup.py`.

## Recall experiment

```text
source document → prepare.py → draft notes + questions.json
                            → scoring/answer-key.json
reviewed corpus → Basic Memory → client-specific runners → raw evidence
                                                        → verifiers → score.py
```

`evaluation/recall/prepare.py` is an authoring tool with a pinned source revision, not a runtime
dependency. The answer key belongs only to the evaluator. Client runners and
verifiers in `evaluation/{claude,codex,opencode}/` own their clients' differing
configuration, event streams and tool-inventory checks. `evaluation/recall/score.py` grades
normalized retrieval results; it does not verify tool restrictions or provenance.
Keep raw-evidence verification separate from scoring.

## Native runtime and verification

The [quickstart](../README.md#connect-your-coding-agent) shows how to enable the
optional `shared-memory-approval-gate` (`approval_gate.proxy`), which starts the
native Basic Memory server. `shared-memory-mcp` starts that server directly.
The proxy forwards reads and eligible temporary writes. For a durable write it
returns a proposal that the owner reviews and confirms with `approval_gate.cli`.
Direct connections use chat approval. See
[ADR 0013](adr/0013-technical-approval-for-durable-writes.md) for the write
policy and the rollout decision.

`ops/` and the evaluation harnesses use the native runtime. `ops/` implements
backup, restore and OKF export. `build/semantic_runtime.py` builds the patched
wheel and invokes `evaluation/native/mcp_watcher.py` to verify it.

`evaluation/native/mcp_server_guard.py` blocks inference imports and outbound
Python sockets in disposable child processes. The MCP/watcher probe checks
startup, writes, default/scoped text search, semantic-query refusal, external-file
indexing, idle operation, restart and CLI retrieval. Its integration test runs
the isolated semantic-disable path without installing packages. The two retained
Semantic tests cover patch application from pristine and already-patched sources
and byte-reproducible wheel construction.

The native conditional-write and coverage probes use that guard without any
`workflow` import. Actual-client behavior and temporary context remain under
`evaluation/clients/`. See [Python coding guidelines](python-coding-guidelines.md)
for the lint, type and unit/integration checks.

## Historical workflow implementation

The complete service, SQLite schema, process-wide acceptance hook, facade,
reviewer, version-3 bundles, protected probes and their tests are preserved at
commit
[`fe09180fac127bcaf48c87fc29b3577c49300e61`](https://github.com/simonsilie/harness-independent-shared-memory/tree/fe09180fac127bcaf48c87fc29b3577c49300e61).
They are no longer active packages or CI prerequisites. The archived
[architecture and transaction contracts](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/docs/repository-architecture.md#workflow-implementation)
and [design](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/docs/phase-1b-workflow-design.md)
retain their original details. Follow the [archive reproduction instructions](archive/custom-code-decision.md#historical-reproduction)
only for historical verification, not productive deployment.
