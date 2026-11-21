# Basic Memory runtime patches

`basic-memory-semantic-disable.patch` adds `semantic_search_enabled` to the
installed Basic Memory 1.0.0 source. With explicit owner approval, it was applied
to the project's `.venv` on 17 November 2026 and verified there with disposable
data; see [installation evidence and backup](../docs/model-free-operation.md#approved-local-installation).
It has not been enabled in the external storage configuration. It is not an
upstream release or a dependency change, and must be reapplied after a reinstall.

With the patch applied, either configuration form disables the semantic stack:

```json
{"semantic_search_enabled": false}
```

```sh
BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED=false
```

The default is `true`, preserving existing behavior. Changing the setting requires
restarting the service. When disabled:

- SQLite and PostgreSQL search repositories skip embedding providers, rerankers
  and vector adapters, including providers injected into their constructors.
- Background vector synchronization is skipped; native storage, materialization,
  full-text indexing and text retrieval remain available.
- Default searches use text, including multi-project search and configurations
  previously selecting hybrid. Explicit vector/hybrid queries return the existing
  semantic-unavailable error rather than silently changing retrieval mode.
- Config loading skips model-dependent reranker validation even if reranking was
  enabled. Inactive embedding/reranker provider settings are left intact.
- Existing notes and indexes are not deleted. This patch disables use of the local
  semantic stack; it does not configure a separately hosted remote service.

The seven changed source files cover settings, runtime capability detection,
both repository constructors, both search composition paths, default MCP search
selection and the shared vector-sync boundary. The patch is based on the installed
source, not an assumed upstream Git revision. Review and revalidate it when
changing Basic Memory versions.

## MCP project creation

`basic-memory-mcp-project-create.patch` blocks `bm_project(command="create")`
by default. `list`, `recent`, and the administrative `basic-memory project add`
command remain available. To enable creation for a trusted MCP server, set
`"enable_mcp_project_create": true` in the server's `config.json` or set
`BASIC_MEMORY_ENABLE_MCP_PROJECT_CREATE=true` in its environment and restart it.

The wheel below includes both patches. Install that wheel to make the setting
available in the runtime used by the clients.

## Reproducible runtime build

`build/semantic_runtime.py` combines the source pin and both patches into one
versioned wheel. It reads Basic Memory's version, wheel URL and SHA-256 from
`uv.lock`, downloads that exact wheel, verifies the hash, applies both patches
with zero fuzz and repacks the result as `1.0.0+semantic.2`. The local version
suffix identifies this patch integration; increment `BUILD_REVISION` in the build
script when a patch changes. Wheel entries are sorted and carry fixed
timestamps, so a rebuild is byte-identical. The hashes of the pinned wheel, both
patches and the output are recorded in `build/dist/manifest.json`. Pass
`--wheel <pinned wheel>` to build from a local copy offline; the hash is still
verified against the lock.

```sh
uv run --locked python build/semantic_runtime.py build
uv run --locked python build/semantic_runtime.py verify
```

`verify` first compares the wheel's SHA-256 with `wheel_sha256` in the manifest,
so the run is bound to the documented artifact. It then installs the wheel and
the locked runtime dependencies into a fresh `build/.verify-venv` and runs the
[existing watcher probe](../evaluation/native/mcp_watcher.py) with
`--installed-semantic-disabled`. It passes only when the built package starts
over MCP, writes a note, finds it with the default text search and records zero
inference imports and zero outbound connections in both MCP processes and the
CLI. The probe's expected version is supplied through `PHASE1B_EXPECTED_VERSION`
because the built wheel carries the local version suffix.

Neither command installs into the launcher's `.venv` or changes productive
storage or client configuration. Deploying the wheel to the productive runtime
is a separate, explicit step; the launcher's existing field check then accepts
the built package without further patching.

## Validation without installation

Run from this repository using the existing environment and system `patch`:

```sh
uv run --locked --no-sync pytest -q tests/evaluation/native/test_semantic_disable.py
WATCHFILES_FORCE_POLLING=true uv run --locked --no-sync python evaluation/native/mcp_watcher.py --semantic-disabled
```

Both commands copy the installed Python package into disposable storage and apply
the patch there with zero context fuzz if it is not already present.
The reverse dry run uses `--force` to keep `patch` from automatically retrying
in the other direction under `--batch`, which would misidentify pristine source
as already patched. The regression fixture exercises both pristine and already
patched source, independent of the installed environment.
Subprocesses load that copy through
`PYTHONPATH`; the installed package is untouched. The watcher probe retains the
patched source, applied-patch output and raw evidence under its ignored run folder.
No software is installed and no productive service is started.

The regression test checks JSON/environment configuration, provider/adapter
construction boundaries for both backends, default text selection, skipped empty
and nonempty synchronization, direct constructor injection and preservation of
the enabled provider path. The integration probe exercises MCP startup, note
creation without per-note opt-out, default and scoped text search, explicit
semantic/hybrid refusal, external-file indexing, a 30-second idle period, restart
and CLI retrieval with an unusable provider setting.

The integration comparison leaves the installed SQLite vector extension available
and first verifies it loads in an in-memory database. Inference imports and
outbound Python connections are guarded in both MCP processes and the CLI check.
Passing requires zero blocked-import attempts or outbound connections, no model
files and no physical `search_vector_embeddings` table. Reranking is intentionally
enabled and the configured default mode is hybrid, so neither can bypass the new
switch. No live PostgreSQL server, remote routing or re-enabling against existing
vector data was exercised.

To check the installed package directly, without copying or patching it:

```sh
WATCHFILES_FORCE_POLLING=true uv run --locked --no-sync python evaluation/native/mcp_watcher.py --installed-semantic-disabled
```

This uses the same disposable data and guards, and verifies the actual installed
import path in both MCP processes and the CLI. It requires the patch to be installed.

The existing unpatched fallback check remains available separately:

```sh
WATCHFILES_FORCE_POLLING=true uv run --locked --no-sync python evaluation/native/mcp_watcher.py
```
