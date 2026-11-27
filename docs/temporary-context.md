# Temporary context and archive behavior

The active shared-client rules are recorded in
[shared-memory-lifecycle.md](shared-memory-lifecycle.md). They use the existing
four native tools and logical archival in place. No daemon, adapter, deletion
operation or additional dependency is needed. After explicit owner approval,
the verified addition was activated in the dotfiles shared AGENTS file on
17 November 2026.

## Rules and activation

Temporary notes use `kind: temporary`, `status: active` and UTC `last_activity`.
Their deadline is seven days after the last work update, extended only by an
explicit owner's later `extended_until`. Reading does not refresh activity.
Completion archives immediately, regardless of an extension. Ordinary recall
checks temporary metadata before using results, excludes expired/completed notes
even if maintenance fails, and conditionally persists archival on access.
There is no background transition exactly when a deadline passes.

Archive search is explicit. Restore refreshes activity and clears archival,
completion and extension fields. Content remains until explicit owner-requested
deletion. All updates use native `expected_checksum`; conflicts preserve the
winning version. Durable promotion still requires separate chat approval.

The lifecycle rules are part of the shared agent instructions. Start new
sessions to load changes to those instructions. Activation evidence stays local.

## Verification

```sh
uv run --locked --no-sync python evaluation/clients/lifecycle.py
# To check only one installed client:
uv run --locked --no-sync python evaluation/clients/lifecycle.py opencode
```

The probe reuses [the existing client runners](../evaluation/clients/behavior.py)
with a per-run candidate instruction override. Codex receives the candidate as
`developer_instructions`; OpenCode loads it through its `instructions` array.
The installed global instructions and ordinary coding tools remain available.
Only native server routing points to disposable model-free stores beneath
`evaluation/clients/runs/`. Live client state uses its normal locations; no
software is installed. These are candidate behavior checks, not proof of global
activation or enforcement by the memory server.

Fixtures include active entries authored eight days ago, a seven-day boundary,
a future extension, an elapsed extension, a completed entry with a future
extension and an existing archive entry. The clients save a new handover and
resume it in a fresh session using an unpredictable token. Subsequent turns
update work, extend availability, complete work, search the archive explicitly
and restore an entry. Checks inspect native files and tool arguments as well as
answers. Two independent native MCP sessions then read the same temporary note;
the winner updates it and the stale write must return `REVISION_CONFLICT` while
preserving the winning API content, checksum and file bytes. This complements
[earlier actual-client conflict checks](native-client-writes.md).

The small fixture fits on one result page. The instruction requires collecting
all pages before mutation, but this probe does not verify large-store pagination.
Expiry uses authored timestamps, not a seven-day wait. Native storage remains
responsible for checksums; correct client interpretation remains a convention.

## Global activation verification

The post-activation probe `.state/lifecycle-setup/verify-activation.py` starts
fresh installed-client sessions without a candidate instruction override. Only
MCP server routing is changed to use disposable stores. It checks scoped recall
of an unpredictable extended-handover token, exclusion of all expired/completed
tokens, conditional archival in native files, and unchanged productive notes
and corpus. Evidence is retained in
`evaluation/clients/runs/20261117T204004.633727Z/`.
Both clients passed; the run's `result.json` confirms the checks and unchanged
productive notes/corpus. Per-client results are in `activation-verified.json`.

An initial attempt at `20261117T203858.241969Z` used the existing Codex runner's
`sandbox: read-only`. Codex correctly excluded inactive entries and reported that
it could not persist archival in that mode. For the actual activation check, the
local probe uses the runner with `sandbox: workspace-write`, matching normal
working sessions; it does not change the tracked runner's default or override
the activated memory rules. The original read-only trace remains retained.

## Retained findings and corrections

The first sandboxed attempt (`20261117T184419.381984Z`) could seed the native
store but could not start Codex's normal SQLite session state. Real-client checks
therefore require normal process, socket and client-state permissions.

Codex's initial six-turn check is retained at
`evaluation/clients/runs/20261117T184505.481298Z/`. Capture, fresh-session recall,
expiry, extension, updates, completion and explicit archive search worked.
An overly specific German phrase assertion was corrected to check the retained
subject rather than one grammatical wording; model turns were not repeated for
that assertion. The native files also exposed a substantive restore issue:
`bm_write` merges existing frontmatter, so omitting archive fields does not clear
them. The model's claim that the fields were removed was rejected by file checks.

A native probe confirmed that explicit YAML `null` values in content frontmatter
clear their meaning, while retaining the null keys in the file. Passing nulls
through the separate `metadata` argument is unsupported. The candidate now
requires explicit nulls and a read-back check. Source: installed Basic Memory
`services/note_preparation.py:prepare_update_entity_content` and
`markdown/utils.py:schema_to_markdown`; reproduction is retained in
`.state/lifecycle-setup/probe-null.py`. The corrected Codex restore turn is in
`codex-restore-corrected/` under the original run.

The first OpenCode capture (`20261117T184803.013804Z`) saved correctly without
ordinary recall. The original probe incorrectly required unrelated expiry
maintenance during that save. The assertion now checks archival after the fresh
session's ordinary recall, which is the actual convention. The complete repeat
uses the corrected restore rule at `20261117T185009.012073Z`.

Final checks of both retained client traces passed, recorded as
`codex-resume/verified-final.json` under the Codex run and
`opencode-resume/verified-final.json` under the OpenCode run. The corrected Codex
restore trace replaces only its original restore turn. The final validator
`.state/lifecycle-setup/verify-retained.py` checks exact continuation tokens,
ordinary scope, exclusion of inactive/archive tokens, final native metadata,
retention and temporary conflicts without repeating model turns. The conflict
probe now establishes a native read-back baseline after the winning write before
comparing checksums, content and file bytes across the rejected stale write;
the earlier probe's failed immediate file-content assertions remain retained.
Both final native two-session conflict checks passed. The two productive personal
notes still match their approved checksums, no productive fixture notes were
introduced, and Git reports no corpus changes. Only an uninterrupted invocation
of the full probe writes its top-level `result.json`; the split retained checks
above are the evidence for this session.

## Frontmatter reset

Reset optional lifecycle fields explicitly to YAML `null` in content
frontmatter and read back the result. Native `bm_write` preserves omitted
frontmatter fields. The separate `metadata` argument rejects nulls. The
native probe and the restore checks above verify this behavior.

## Repository checks

Ruff lint passes repository-wide. The changed Python files pass formatting and
Pyrefly. Repository-wide formatting still reports five unchanged historical
files; Pyrefly still reports 11 errors in unchanged code. The isolated suite has
85 passes and 22 passing subtests, with the same five failures caused by the
historical source/corpus pin mismatch. Integration tests pass: 19 tests and nine
subtests. No source pin or corpus content was changed. Checks use the installed
environment with `UV_CACHE_DIR=.uv-cache UV_NO_SYNC=1 UV_OFFLINE=1`.
