# Project: harness-independent-shared-memory

Python evaluation harness for a read-only recall experiment on Basic Memory as
shared memory. `evaluation/recall/prepare.py` builds a 20-note corpus and 22-question set from a
single source document; the `evaluation/` harnesses (OpenCode, Codex, recovery)
run clients against Basic Memory and verify they used only the allowed
`bm_search`/`bm_read` tools, retrieved and read the right notes, and left the
corpus bytes unchanged. `evaluation/recall/score.py` grades the results.

Write all repository documentation in English.
Use synthetic data and placeholder paths in public documentation, tests and
fixtures. Keep live notes, machine configuration and raw run evidence outside
Git. Pass only the settings needed by a test when writing fixture configuration.

## Session Learnings

If you hit a non-obvious problem during a session — something that wasted time,
caused a wrong approach, or revealed a convention not documented here — propose
an update to AGENTS.md or the relevant skill and a concise note for the Basic
Memory shared-memory database before finishing. Include the supporting source
and relevant project context, and check for existing notes before proposing a
new one. Only capture things that would trip up future sessions, not one-off
issues. Frame learnings as positive conventions (what to do) rather than
reactive rules (what not to do). Wait for explicit approval before saving the
proposed updates; approval for one destination does not imply approval for the
others.

- Claude Code emits its `init` tool inventory only after a prompt is submitted.
  To capture it without a model request, add a `UserPromptSubmit` hook that
  exits 2 (see `evaluation/claude/run.py --verify-only`).
- When launching `claude` from inside a Claude Code session, strip the
  inherited `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`,
  `CLAUDE_CODE_SESSION_ATTENDED` and `CLAUDE_CODE_MESSAGING_*` variables so the
  evaluated client runs as an independent session.
- OpenCode resolves a session's project configuration from the git project
  root, so a disposable `.opencode/opencode.json` written into a run workspace
  is never discovered. Inject a disposable configuration over the live one with
  the undocumented `OPENCODE_CONFIG_CONTENT` environment variable (an inline
  JSON merge, analogous to `OPENCODE_CLI_CONFIG_CONTENT`), keeping the client
  in the real checkout. The experimental MCP connect endpoint
  (`POST /api/experimental/mcp/{server}/connect?location[directory]=...`) only
  works after a first `opencode run` has opened the location, which is why the
  harnesses run a readiness turn before connecting.
- Match real-client tool responses by call ID or exact arguments rather than
  transcript position: parallel calls can complete out of order. The protected
  eligibility probe observed OpenCode's second search finishing before its first
  (see the archived [`eligibility_lifecycle.py`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/evaluation/workflow/eligibility_lifecycle.py) and
  `evaluation/phase1b/runs/20261116T113301.888339Z-real-clients/opencode-immediate-1.events.jsonl`).
- During workflow restore, keep native configuration and project paths inside
  staging until activation: Basic Memory ORM reads can create configured
  directories. Run native reindexing in a separate process with
  `BASIC_MEMORY_CONFIG_DIR` pointing to staging (see the archived
  [`workflow/integration.py`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/integration.py)
  and [`workflow/bundle.py`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/workflow/bundle.py)).
- Use `--force` for directional patch checks, including reverse dry runs, and
  test both pristine and already-patched sources. This keeps `patch --batch`
  from automatically retrying in the opposite direction and misidentifying
  pristine source as already patched (see `patches/README.md` and
  `tests/evaluation/native/test_semantic_disable.py`).
- For standalone SQLite backups, close database connections and convert the
  copied snapshot to `journal_mode=DELETE` before computing its manifest.
  Verify that repeated reads and restores leave the backup unchanged: WAL/SHM
  sidecars can change even during read-only inspection (see
  `ops/recovery.py` and
  `tests/ops/test_recovery_integration.py::test_wal_snapshot_remains_reusable_after_reads`).
- Verify that the export reader works without Basic Memory by running it in a
  fresh Python process with imports of `basic_memory` and its submodules blocked.
  A before-and-after comparison of `sys.modules` can miss imports that reuse a
  module already cached by pytest (see `tests/ops/test_export_integration.py`).
- When reviewing MCP permissions, check permitted subcommands as well as tool
  names. In Basic Memory 1.0.0, `bm_project` supports both project discovery and
  project creation (see `basic_memory/mcp/tools/projects.py` in the installed
  package and the productive allowlist in `README.md`).
- When copying from a mutable source, anchor traversal to an open descriptor for
  a trusted root directory. Open children relative to their open parent with
  `O_NOFOLLOW | O_NONBLOCK`, check their type with `fstat()`, and read regular
  files through the same descriptor. Create the destination directory before
  copying entries so empty directories are preserved (see `ops/recovery.py`
  and `tests/ops/test_recovery_integration.py`).
- Verify stdio write gates by sending the request through the actual proxy to a
  disposable native store. Bound reply waits and assert the resulting store
  state (see `tests/approval_gate/test_native_integration.py`).
- After a native Basic Memory write in a short-lived stdio session, close stdin
  and wait for graceful exit with a deadline. Basic Memory drains accepted
  writes during shutdown. Check the Markdown after process exit in integration
  tests (see `approval_gate/native.py` and `tests/approval_gate/test_gate.py`).
- Verify the approved project UUID in the native session that will execute
  the write. `BASIC_MEMORY_MCP_PROJECT` can take precedence over an explicit
  UUID (see `tests/approval_gate/test_native_integration.py`).
- In stdio subprocess tests, set a deadline for each expected reply and
  terminate and reap the child on timeout. A live child can keep stdout open
  without replying. See the bounded MCP calls in
  `evaluation/native/mcp_watcher.py`.
