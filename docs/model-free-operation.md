# Model-free operation of the installed candidate

Checked on 17 November 2026 against the project environment:
Basic Memory 1.0.0, SQLite, Python 3.14. The initial unmodified-package findings
below are retained as evidence. The subsequently approved local installation
passes model-free checks; see [installation verification](#approved-local-installation).
No productive configuration was changed.

## Initial unmodified-package result

The installed candidate does not provide a verified global configuration for
model-free operation. Its SQLite vector extension is present, semantic search
starts enabled, and the provider setting accepts `fastembed`, `openai` or
`litellm`, with no supported off value. Explicit text search and per-note
`embed: false` do not disable background vector synchronization globally.

The installed-stack comparison booted the MCP server and created a note without
an embedding opt-out. With inference imports blocked but `sqlite_vec` available,
the default search failed with `fastembed package is missing`. The guard recorded
three FastEmbed import attempts and zero outbound connections. Background note
materialization also logged `Vector sync after materialization failed` and a
FastEmbed dependency error. This demonstrates an inference dependency, rather
than assuming that offline environment variables disable inference.

## Reproduction

Run from the repository root using the existing environment:

```sh
uv run --locked --no-sync python evaluation/native/mcp_watcher.py --installed-semantic-stack
WATCHFILES_FORCE_POLLING=true uv run --locked --no-sync python evaluation/native/mcp_watcher.py
```

The first command is a negative comparison and currently exits nonzero on the
default-search assertion. Both runs use disposable configuration, database,
notes and empty model-cache paths under `evaluation/native/runs/`. They block
inference imports and outbound Python sockets. Only the control additionally
blocks the SQLite vector extension; this is a simulated missing dependency,
not a deployable configuration switch.

Installed-stack evidence: `evaluation/phase1b/runs/20261117T153251.376708Z/`,
especially `server-1.guard.json`, `mcp-write.json`, `mcp-default-search.json`
and `state/basic-memory.log`. Run artifacts are locally retained and ignored by
Git. The earlier successful fallback evidence is documented in the
[native coverage inventory](historical-capability-inventory.md), entry E5.

The control run, `evaluation/phase1b/runs/20261117T153413.702098Z/`, passed:
startup, write, default text retrieval, external-file indexing, a 30-second dwell
and read/search after restart. It recorded zero FastEmbed import attempts, no
downloaded model files and an unchanged historical corpus. Explicit vector
search was refused cleanly, and provider `none` failed at startup as expected.

The initial control, `evaluation/phase1b/runs/20261117T153256.057715Z/`, timed
out waiting for external-file indexing with the native filesystem watcher.
Repeating with Watchfiles' polling override passed. Use that override to
reproduce the control in this environment; the cause of native event delivery
failure has not been established. Polling does not disable semantic indexing.

## Requirement gap and smallest remedy

[ADR 0007](adr/0007-model-independent-storage-and-text-search.md) requires
storage, text retrieval, startup and background indexing without inference or
model downloads. A supported instance-wide semantic-disable setting must skip
provider construction, vector setup and background embedding work while leaving
text indexing enabled. That is the smallest product remedy indicated by this
check; it had not yet been implemented or installed at that point.

Keeping `sqlite_vec` unavailable exercises the native text-only fallback, but
changing installed dependencies requires a separate decision and is not an
established productive configuration. This left the first roadmap item open
until the patched installation below satisfied the complete model-free requirement.

## Local implementation prepared for review

The [semantic-disable patch](../patches/basic-memory-semantic-disable.patch) adds
`semantic_search_enabled` (default `true`) and the corresponding
`BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED` environment setting. Setting it to `false`
skips provider construction, vector setup, reranking and background vector sync;
default retrieval becomes text even when the configured default is hybrid.
Explicit semantic/hybrid searches are refused. The [patch notes](../patches/README.md)
describe its scope and reproduction commands.

The isolated patched-package run
`evaluation/phase1b/runs/20261117T162840.415976Z/` passed startup, storage, default
and scoped text retrieval, filesystem watcher indexing, a 30-second dwell,
restart and CLI retrieval. The installed SQLite vector extension was available
and verified loadable (`v0.1.10-alpha.4`), rather than blocked to induce fallback.
Both MCP processes and the CLI guard recorded zero inference imports and zero
outbound connections; no model files or physical vector-embedding table were
created. The historical corpus was unchanged.

The focused regression test passed configuration/environment parsing, disabled
construction paths for SQLite and PostgreSQL, skipped vector sync and the enabled
provider path. PostgreSQL was not exercised against a live database. The existing
unpatched fallback probe also passed in
`evaluation/phase1b/runs/20261117T162744.231138Z/`.

Revalidation in `evaluation/phase1b/runs/20261117T164955.741304Z/` passed the same
isolated MCP/watcher/restart/CLI checks and the focused regression test (`1 passed`).

## Approved local installation

On 17 November the owner explicitly approved installation. The seven-file patch
was applied with zero context fuzz to `.venv/lib/python3.14/site-packages/basic_memory/`.
Original files and a manifest with before/after SHA-256 hashes are retained at
`.state/semantic-disable-install/20261117T165529.159220Z/`. No dependencies were
added or upgraded; package metadata still reports 1.0.0. Reinstalling Basic Memory
replaces the local modification, so reapply and revalidate the patch after any
environment rebuild. Review it against new source before changing versions.

Reproduce the installed-package verification from the checkout:

```sh
uv run --locked --no-sync pytest -q tests/evaluation/native/test_semantic_disable.py
WATCHFILES_FORCE_POLLING=true uv run --locked --no-sync python evaluation/native/mcp_watcher.py --installed-semantic-disabled
```

Run `evaluation/phase1b/runs/20261117T165541.757500Z/` passed MCP startup, note
creation without per-note opt-out, default and scoped text search, explicit
vector/hybrid refusal, watcher indexing, 30 seconds idle, restart and CLI retrieval.
Configuration set `semantic_search_enabled=false`, with hybrid defaults and
reranking enabled to exercise the global override. Both MCP processes and the CLI
recorded and verified their import path against the installed package, without a
`PYTHONPATH` package copy. All three guards recorded zero inference imports and
zero outbound connections. SQLite's vector extension remained loadable; no model
files or vector-embedding table were created. The historical corpus was unchanged.
The focused regression test passed (`1 passed`); Ruff and Pyrefly passed for the
three affected probe/test files.

This completes the model-free implementation check for the locally patched SQLite
installation. A live PostgreSQL service, remote routing and re-enabling existing
vector data remain untested. External storage and client configurations were not
changed; productive activation and verification remain separate roadmap tasks.

## Reproducible build verification

A manual patch after every environment rebuild is no longer the only way to get
that runtime. The [versioned build step](../patches/README.md#reproducible-runtime-build)
produces `basic_memory-1.0.0+semantic.1-py3-none-any.whl` from the wheel pinned in
`uv.lock` and the same seven-file patch; two builds produced the identical SHA-256
`c9e847b2306ab4e0484d38e8e96e72c6b8d144760ff176ceec3c705b542efc82`.

`build/semantic_runtime.py verify` compares the wheel's SHA-256 with the manifest
before installing it, then installs that wheel with the locked runtime
dependencies into a fresh `build/.verify-venv` and runs the existing
watcher probe with `--installed-semantic-disabled`. The run at
`evaluation/workflow/runs/20261118T112522.916579Z/result.json` passed MCP startup,
note creation without an opt-out, default and scoped text search, explicit
vector/hybrid refusal, external-file indexing, a 30-second dwell, restart and CLI
retrieval with the SQLite vector extension available. All three guard files
recorded `blocked_imports: []` and `blocked_connections: 0` and resolved the
installed built package. No model files or vector-embedding table were created and
the historical corpus was unchanged. This verifies the built artifact, not a
deployment into the launcher's runtime; live PostgreSQL and remote routing remain
untested.
