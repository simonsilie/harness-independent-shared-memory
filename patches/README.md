# Historical Basic Memory runtime patch

The project now uses the official Basic Memory wheel and restricts project
creation through the MCP approval gate. The previous runtime was the published
[Basic Memory 1.0.0+project.2 wheel](https://github.com/simonsilie/harness-independent-shared-memory/releases/tag/basic-memory-project.2).
The original patch and builder are available in the
[checkout before migration](https://github.com/simonsilie/harness-independent-shared-memory/tree/c29fc23ca214b2971c7b76fb0fdbb2e478ddbf0e).
The [model-free operation report](../docs/archive/model-free-operation.md) records
the earlier semantic-disable patch and its validation.

## MCP project creation

`basic-memory-mcp-project-create.patch` blocked `bm_project(command="create")`
by default. `list`, `recent`, and the administrative `basic-memory project add`
command remained available. To enable creation on that patched runtime,
set `"enable_mcp_project_create": true` in the server's `config.json` or set
`BASIC_MEMORY_ENABLE_MCP_PROJECT_CREATE=true` in its environment and restart it.

## Reproducible runtime build

In the historical checkout, `shared_memory/runtime_build.py` pins the original
upstream version, wheel URL and SHA-256. It downloads the upstream wheel, verifies the hash, applies the
project-creation patch with zero fuzz and repacks the result as
`1.0.0+project.2`. The builder suppresses patch backups so an offset cannot add
files to the wheel. Increment `BUILD_REVISION` when the patch changes. Wheel
entries are sorted and carry fixed timestamps, so a rebuild is byte-identical.
The input, patch and output hashes are recorded in `build/dist/manifest.json`.
Pass `--wheel <pinned wheel>` to build from a local copy offline with the same
hash check.

```sh
uv run --locked python shared_memory/runtime_build.py build
uv run --locked python shared_memory/runtime_build.py verify
```

`verify` checks the wheel against its manifest, installs it with the locked
dependencies into `build/.verify-venv` and runs the
[historical watcher probe](https://github.com/simonsilie/harness-independent-shared-memory/blob/c29fc23ca214b2971c7b76fb0fdbb2e478ddbf0e/evaluation/native/mcp_watcher.py)
with `--installed`. The
probe checks MCP startup, writes, indexing and text recall while simulating an
unavailable vector runtime. It uses `NATIVE_MCP_EXPECTED_VERSION` to check the
wheel's local version suffix.

To deploy a new build, publish the versioned wheel and update its version and
source in `pyproject.toml` and `uv.lock`.
