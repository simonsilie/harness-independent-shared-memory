# External local storage

The storage layout was created and activated on 17 November 2026 under
`$HOME/SharedMemory`, outside this checkout and Git, with explicit owner approval.
The native SQLite database is initialized with both prepared projects and
`semantic_search_enabled=false` using the [installed model-free patch](model-free-operation.md#approved-local-installation).
This is the designated productive store. [Codex and OpenCode now connect](../client-connections.md)
through the shared dotfiles launcher; their historical corpus connections have
been replaced in both global and active project configuration.

## Actual layout

| Path relative to `$HOME/SharedMemory` | Purpose |
| --- | --- |
| `state/config.json` | Native Basic Memory configuration, SQLite backend, text search default, semantic search, automatic updates and Logfire disabled |
| `state/memory.db` | Initialized native SQLite database; project associations and text-search indexes verified |
| `notes/personal/` | Native `personal` project, also the configured default project |
| `notes/projects/harness-independent-shared-memory/` | Native project for this checkout |
| `durable/`, `temporary/`, `archive/` within each note project | Prepared content folders; empty, with lifecycle still to be configured |
| `observations/observations.jsonl` | [Automatic lightweight observations](automatic-observations.md), activated on 18 November 2026; outside indexed note roots |

The two native project roots are siblings, so neither contains the other.
The database/configuration and observations are outside both indexed note roots.
The native configuration contains absolute paths resolved from the actual home
directory; this document uses `$HOME` to avoid recording the account name in Git.
There is one designated target store shared by future clients, not one per client.

The active configuration contains these values:

```json
{
  "projects": {
    "personal": {"path": "$HOME/SharedMemory/notes/personal", "mode": "local"},
    "harness-independent-shared-memory": {
      "path": "$HOME/SharedMemory/notes/projects/harness-independent-shared-memory",
      "mode": "local"
    }
  },
  "default_project": "personal",
  "database_backend": "sqlite",
  "database_url": null,
  "default_search_type": "text",
  "semantic_search_enabled": false,
  "auto_update": false,
  "logfire_enabled": false
}
```

`$HOME` above is documentation notation: the installed JSON has expanded paths.
`semantic_search_enabled=false` disables the semantic stack globally in the
patched installation; a text-search default alone would not do so.
Both client connections use this configuration directory and explicit
personal/current-project scopes. From the checkout, the native MCP service can
be started on demand with the verified configuration:

```sh
BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemory/state" \
BASIC_MEMORY_HOME="$HOME/SharedMemory/notes/personal" \
BASIC_MEMORY_FORCE_LOCAL=true WATCHFILES_FORCE_POLLING=true \
uv run --locked basic-memory mcp --transport stdio
```

The verification processes have stopped; no persistent daemon was installed.
The experiment's `./evaluation/bm` launcher still targets the historical corpus and must
not serve productive memory. `uv sync --locked` rebuilds `.venv` with the patched wheel.

## Preservation and verification

Before creation, the target did not exist and no ancestor was a Git checkout.
Creation refused an existing destination and used private permissions: directories
are mode `0700`, configuration and the empty JSONL log are mode `0600`.
The written JSON was read back and compared with the prepared configuration;
project directories, empty content and absence of a database were verified.
At that preparation stage, no native Basic Memory startup or configuration
loader was used.

Immediately before activation, both prepared note roots were still empty and
the external database did not exist. A copied snapshot of the default database
at `$HOME/.basic-memory` still contained one project and zero entities/note-content
rows; `$HOME/basic-memory` contained no Markdown notes. The original default
deployment, its model cache, its note root and the historical corpus were hashed
before and after activation and remained unchanged. No content was migrated.
Client configurations and the historical launcher were preserved.

Activation changed only the external configuration's semantic-disable setting
before native startup. The previous configuration, effective configuration,
preservation hashes, tool responses and guards are retained under the ignored
`.state/external-storage-activation/20261117T170024.875115Z/`; the activation
script is at `.state/external-storage-activation/activate.py`. It is a one-time
initialization check and refuses an existing database. The earlier prepared
configuration remains at `.state/productive-storage-plan/config.json` as historical
evidence, rather than the active configuration.

One temporary note was created through MCP in `personal`; another was written
as an external file in the checkout's memory project and indexed by the watcher.
After restarting MCP, reads and default text searches found both notes in their
respective projects. Combined search found both; personal-only search excluded
the project note. Both check notes were then deleted with native checksum guards,
and subsequent searches were empty. The final database has zero active entities,
the exact two configured project paths, no vector-embedding table and a passing
SQLite integrity check. No Markdown check files remain.

All three MCP processes used the installed patched package and recorded zero
inference-import attempts and zero outbound connections. No models were created
in the empty activation cache. Native state files are mode `0600`; directories
remain `0700`, and processes ran with a private umask. The observation log remains
empty. Backup, restoration, portable export, lifecycle rules and automatic
observation recording retain their own roadmap tasks.
