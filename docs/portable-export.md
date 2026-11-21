# Portable export

Export project by project into storage outside repositories and indexed note
roots. Verify the Markdown and YAML output with an independent reader. This
implements [ADR 0009](adr/0009-portable-memory-export.md) alongside the separate
[same-version backup and restoration procedure](productive-backup.md).

## Export format

Native `basic-memory okf export` writes one OKF v0.2 bundle per project. A bundle
is plain Markdown with YAML frontmatter:

| Path in the export | Content |
| --- | --- |
| `bundles/<project>/index.md` | Bundle root with `okf_version: "0.2"` and links to the content folders |
| `bundles/<project>/<folder>/index.md` | Folder index listing the notes below it |
| `bundles/<project>/<folder>/<note>.md` | Note body, authored frontmatter and `bm.okf_export` extension |
| `bundles/<project>/log.md` | Best-effort recorded change history |

The bundle directory name is the project name, and every note permalink carries
that project prefix (`<project>/<folder>/<note>`). Project associations therefore
survive as directory names plus permalinks; there is no separate association file.
Authored lifecycle metadata (`kind`, `status`, `last_activity`, `archive_reason`,
`completed_at`, `archived_at`) is ordinary frontmatter and is exported verbatim.
`bm.okf_export` records the exporter version and exported relations. Wiki links
become standard Markdown links, and non-Markdown assets are preserved.

Exported files are private (`0600`, directories `0700`), matching the store.

## Procedure

Enumerate the configured projects rather than exporting only the default one; a
single project's bundle is not the complete store. The `export` command in the
[`ops` package](../ops/), alongside `backup` and `restore`, does this and writes
one `bundles/<project>` directory per configured project:

```sh
uv run --locked --no-sync python -m ops export \
  "$HOME/SharedMemory" "$HOME/SharedMemoryExports/<identifier>"
```

On success, `ops` prints the destination path as the last stdout line; the
native `okf export --json` diagnostics appear before it.

Then validate each bundle with `uv run --locked --no-sync basic-memory okf check <bundle> --json` and verify
the result independently with a generic Markdown/YAML reader. The [integration
test](../tests/ops/test_export_integration.py) in this repository builds a
synthetic two-project store with active, expired and archived notes, runs the
same command and reads the bundles without importing Basic Memory. It runs from
a fresh checkout and commits no memory content. The earlier one-off script and
its productive evidence remain private under `.state/portable-export/`. Take a
new export after meaningful memory changes; there is no scheduler.

## Verification evidence

The export verification confirmed that each bundle passed `okf check`, that
project associations were preserved and that the live store was unchanged.
Detailed export evidence stays with the local verification run.

The [integration test](../tests/ops/test_export_integration.py) uses disposable
projects with active, expired and archived handovers alongside durable notes.
The fixture generates activity timestamps relative to execution time and
verifies that bodies and lifecycle metadata survive in the correct project
bundle. An independent reader parses Markdown and YAML and answers scoped
queries directly from the export files.

## Limits

This is a static, readable copy, not a recoverable backup: it contains no native
entity IDs, revisions or full database history, and `log.md` history is
best-effort. Restoring it into Basic Memory or another implementation requires
importing the Markdown and rebuilding indexes; no alternate-engine import was
performed here. Search indexes are intentionally not exported and can be rebuilt
from note content. Each project bundle is exported independently, so take the
export when no writes are in flight; it is not a cross-project transaction.
Export files must be re-created after memory changes and kept private; the export
is on the same computer, so it does not protect against loss of that computer.
