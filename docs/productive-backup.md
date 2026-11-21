# Productive backup and restoration

On 18 November 2026, the actual `$HOME/SharedMemory` store was backed up to
`$HOME/SharedMemoryBackups/20261118T063700Z` and restored independently at
`$HOME/SharedMemoryRecovery/20261118T063700Z`. Both destinations are outside
repositories and indexed note roots. The live store and client configuration
were unchanged. This implements the local recovery requirement in
[ADR 0006](adr/0006-local-memory-outside-version-control.md); portable export
remains a [separate roadmap task](ROADMAP.md).

## Procedure

Use the existing patched Basic Memory 1.0.0 project environment. From this checkout,
choose a fresh identifier for each backup and run:

```sh
uv run --locked --no-sync python -m ops backup \
  "$HOME/SharedMemory" "$HOME/SharedMemoryBackups/<identifier>"
```

On success, `ops` prints the destination path as the last stdout line.

This is an on-demand local procedure: take a new snapshot after meaningful memory
updates and before changing the installed memory software. No scheduler or
retention deletion is installed. A copy on the same computer does not protect
against loss of that computer or its disk.

Backup, restore and [portable export](portable-export.md) are bundled as the
three stable commands of the [``ops`` package](../ops/). The
[implementation](../ops/recovery.py) uses SQLite's online
backup API, including committed WAL data, rather than copying a live database
file. It copies all configured local project trees, empty directories, the
ignore rules, configuration and observation log. The observation log is read
under a shared lock compatible with the writers' exclusive locks. Its snapshot
is independent of the database transaction; observations do not participate in
native note transactions. Runtime logs, watcher status and SQLite sidecars are
excluded.

In a private directory next to the destination, it verifies database integrity, foreign keys,
project associations, the complete Markdown file set and every file's bytes
against canonical database content/checksum. Concurrent note or configuration
changes that cause disagreement fail the backup. Retry with the same destination
once the writes have settled. The backup appears at its final path after
validation and manifest creation. The manifest lists SHA-256 digests of all payload
files. Files are private (`0600`), directories `0700`.

The snapshot database uses rollback-journal mode so later read-only inspection
cannot mutate WAL/SHM files covered by the manifest. Project paths in its database
and effective configuration are relative to the snapshot root; the original
configuration is retained separately as `state/config.original.json`. All native
tables, identities, history and lifecycle frontmatter are retained. The snapshot
is for same-version recovery with the installed patch, not a portable export or
a guarantee of cross-version compatibility.

Restore only into a new, separate destination:

```sh
uv run --locked --no-sync python -m ops restore \
  "$HOME/SharedMemoryBackups/<identifier>" \
  "$HOME/SharedMemoryRecovery/<identifier>"
```

Restore requires a new destination. It checks the backup manifest, copies the
files into a private sibling directory, and sets the final project paths in both
SQLite and the configuration. After validating the staged files, it renames the
directory into place. Never start native Basic Memory on
the backup itself. To rebuild and check the restored text index, scope every
native command to that destination, for example:

```sh
BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemoryRecovery/<identifier>/state" \
BASIC_MEMORY_HOME="$HOME/SharedMemoryRecovery/<identifier>/notes/personal" \
BASIC_MEMORY_FORCE_LOCAL=true \
uv run --locked --no-sync basic-memory reindex --full --search
```

The restored configuration retains `semantic_search_enabled=false`. Indexing
refreshes technical database timestamps, including `note_content.updated_at`;
it preserves note bodies, checksums, revision counters and authored lifecycle
metadata such as `last_activity`. Activating a recovered store in the clients is
a separate explicit operation; this drill does not switch their connections.

## Verification evidence

On 21 November 2026, snapshot `20261121T075017Z` was created and restored
under the same backup and recovery roots. Basic Memory rebuilt the text index
for all six configured projects and indexed all 14 notes without errors.
After reindexing, all project identities, note contents and checksums, and the
observation log matched the snapshot. The backup still matched its manifest.

### Initial recovery drill

The final [result](../.state/productive-recovery/final/result.json),
[verification script](../.state/productive-recovery/verify.py), native stdout,
stderr and eleven inference/network guard records are retained privately under
`.state/productive-recovery/`. No memory content is committed to Git.

The productive snapshot contained five notes across `personal` and
`harness-independent-shared-memory`: four durable notes and one completed,
archived temporary handover. Restore preserved both project external identifiers
and all native rows before indexing, with only project paths relocated. After
explicitly emptying the restored text index, native `reindex --full --search`
rebuilt it; all five notes passed native reads and project-scoped text searches.
Bodies, checksums, revision counters, lifecycle metadata, ignore rules and the
observation log survived. The live logical note/history state, live note/config/
observation bytes and final backup manifest inventory matched before and after.
The guards recorded zero inference imports and zero outbound connections.

There were no active productive handovers at snapshot time.
[Isolated integration tests](../tests/ops/test_recovery_integration.py)
add active and archived temporary content, exercise WAL-only committed data and
two successive restores, and reject unindexed Markdown, corrupted payloads and
existing restore destinations.

The first drill exposed two constraints, with its artifacts retained alongside
the final run: full native indexing updates technical timestamps, and a WAL-mode
backup could acquire mutable sidecars during inspection. The final implementation
closes database connections and converts the snapshot to rollback-journal mode;
the WAL regression covers repeated inspection/restoration without changing the
backup. The earlier `20261118T063500Z` directories are failed-drill evidence,
not the established recovery copy.

Final repository checks passed: 91 isolated tests and 24 integration tests
(including the five new recovery cases), plus 31 subtests; Ruff lint/format,
Pyrefly and `git diff --check` passed. The first integration run had three
sandbox denials for local TCP binding; the complete rerun with local ports
available passed without code changes to those tests.
