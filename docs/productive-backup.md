# Productive backup and restoration

On 18 November 2026, the actual `$HOME/SharedMemory` store was backed up to
`$HOME/SharedMemoryBackups/20261118T063700Z` and restored independently at
`$HOME/SharedMemoryRecovery/20261118T063700Z`. Both destinations are outside
repositories and indexed note roots. The live store and client configuration
were unchanged. This implements the local recovery requirement in
[ADR 0006](adr/0006-local-memory-outside-version-control.md); portable export
is covered separately in [portable export](portable-export.md).

## Procedure

Use the locked Basic Memory 1.0.0 project environment. From this checkout,
choose a fresh identifier for each backup and run:

```sh
uv run --locked memory-ops backup \
  "$HOME/SharedMemory" "$HOME/SharedMemoryBackups/<identifier>"
```

On success, `ops` prints the destination path as the last stdout line.

This is an on-demand local procedure: take a new snapshot after meaningful memory
updates and before changing the installed memory software. No scheduler or
retention deletion is installed. A copy on the same computer does not protect
against loss of that computer or its disk.

Backup, restore and [portable export](portable-export.md) are bundled as the
three stable commands of the [``ops`` package](../shared_memory/ops). The
[implementation](../shared_memory/ops/recovery.py) uses SQLite's online
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
is for same-version recovery. Use OKF for portable export across implementations.

Restore only into a new, separate destination:

```sh
uv run --locked memory-ops restore \
  "$HOME/SharedMemoryBackups/<identifier>" \
  "$HOME/SharedMemoryRecovery/<identifier>"
```

Restore requires a new destination. It checks the complete backup manifest on a
private copy of the files, before any project paths are rewritten, and sets the
final project paths in both SQLite and the configuration. After validating the
staged files, it renames the directory into place. Never start native Basic
Memory on the backup itself. If a snapshot came back from mutable external
storage, obtain the SHA-256 of its `manifest.json` over a trusted channel and
pass it so the restored copy is checked against that value as well:

```sh
uv run --locked memory-ops restore \
  --expected-manifest-digest <digest> \
  "$HOME/SharedMemoryBackups/<identifier>" \
  "$HOME/SharedMemoryRecovery/<identifier>"
```

To rebuild and check the restored text index, scope every native command to
that destination, for example:

```sh
BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemoryRecovery/<identifier>/state" \
BASIC_MEMORY_HOME="$HOME/SharedMemoryRecovery/<identifier>/notes/personal" \
BASIC_MEMORY_FORCE_LOCAL=true \
uv run --locked --no-sync basic-memory reindex --full --search
```

The snapshot retains the store's persisted search settings and any existing
vectors. For an older text-only snapshot, follow the
[embedding rebuild steps](client-connections.md#build-embeddings-for-an-existing-store)
with `BASIC_MEMORY_CONFIG_DIR` pointing to the restored `state` directory.
Indexing refreshes technical database timestamps, including
`note_content.updated_at`, and preserves note bodies, checksums, revision
counters and authored lifecycle metadata such as `last_activity`. Activate a
recovered store by pointing clients at the restored configuration.

## Verification evidence

The recovery drill restored an isolated copy. It verified project associations,
note contents, checksums, lifecycle metadata and the observation log. Native
reindexing rebuilt text search, and the backup still matched its manifest after
verification. Keep snapshot identifiers and detailed results with the backup.

[Isolated integration tests](../tests/shared_memory/ops/test_recovery_integration.py)
cover active and archived fixtures, WAL-only committed data and two successive
restores. They also reject unindexed Markdown, corrupted payloads and existing
restore destinations.

The first drill exposed two constraints, with its artifacts retained alongside
the final run: full native indexing updates technical timestamps, and a WAL-mode
backup could acquire mutable sidecars during inspection. The final implementation
closes database connections and converts the snapshot to rollback-journal mode;
the WAL regression covers repeated inspection/restoration without changing the
backup. Failed-drill artifacts stay with the local verification evidence.

Final repository checks passed: 91 isolated tests and 24 integration tests
(including the five new recovery cases), plus 31 subtests; Ruff lint/format,
Pyrefly and `git diff --check` passed. The first integration run had three
sandbox denials for local TCP binding; the complete rerun with local ports
available passed without code changes to those tests.
