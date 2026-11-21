# Portable export

On 18 November 2026 the productive `$HOME/SharedMemory` store was exported
project by project into `$HOME/SharedMemoryExports/20261118T081638Z` and inspected
without Basic Memory. The destination is outside repositories and indexed note
roots. This implements the export requirement in
[ADR 0009](adr/0009-portable-memory-export.md); it is separate from the
[same-version backup and restoration](productive-backup.md) and the live store and
client connections were unchanged.

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
become standard Markdown links, and non-Markdown assets are preserved; the
productive store currently has no attachments.

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

The productive export contained both configured projects and all six notes: five
durable notes (two personal defaults, three project learnings) and one completed
and archived project handover. There were **no active productive handovers** at
export time; the archived handover was exported with its full body and lifecycle
fields. Every bundle passed `okf check` with no diagnostics, and every exported
file set matched the native database's configured project and note file set.
Export runs recorded zero inference imports and zero outbound connections; live
note, configuration and observation-log inventories were identical before and
after, as was a complete logical dump of every database table, including
revisions and history.

An isolated fixture, now retained as the committed
[integration test](../tests/ops/test_export_integration.py), covered content
missing from the productive store: one active personal handover, one active but
expired project handover, and one archived project handover, plus durable notes
in both projects. Handover timestamps are
generated relative to execution time; the check asserts that the active handover
lies inside the seven-day window and the expired one outside it, so the fixture
does not silently age into a different lifecycle state. All bodies and metadata,
including archive fields and the old `last_activity`, survived; each note stayed
in its own project bundle with no cross-project leakage.

For usability outside Basic Memory, a reader using only Python's standard library
and a generic YAML parser parsed the bundle indexes, frontmatter and bodies
without importing `basic_memory`, then answered scoped queries directly from the
Markdown. A personal-only query found the Python guidelines and a project-scoped
query for the same text returned nothing; the archived handover was found through
its frontmatter. No search index, database or native code was involved.

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
