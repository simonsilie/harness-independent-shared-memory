# Productive Codex and OpenCode connections

The client launchers use the native Basic Memory service and the external store
at `$HOME/SharedMemory`. The historical corpus remains separate.

## Configuration

This checkout is all a client connection needs. Follow the
[quick start](../README.md#quick-start): run `uv sync --locked`, create the
store with `./init-store.sh`, copy `shared_memory/approval_gate/config.example.json` to
`shared_memory/approval_gate/config.json` and generate each client's entry with the
[snippet generator](../README.md#generate-codex-and-opencode-snippets). Verify the proxy against
disposable stores with
`uv run --locked --no-sync pytest -m integration tests/shared_memory/approval_gate`.

Check the effective server entry, including any project-local override, to see
which command a client will use. Switching productive clients requires explicit
owner approval. After a switch,
restart each affected client and check that `bm_project` with `command="list"`
returns the expected projects. To verify the gate, propose a synthetic durable
note in a disposable project. Check that the client receives a proposal and the
note is absent while approval is pending.

## Launchers

`uv sync --locked` installs two commands into the checkout's `.venv/bin`.
`shared-memory-approval-gate` starts the gate in front of the native server and
requires terminal approval for durable writes. The snippet generator uses it.
`shared-memory-mcp` is an alias for the same gate, so existing entries that
reference this checkout also require terminal approval. The launcher reads
`shared_memory/approval_gate/config.json` or the file given with `--config` or
`SHARED_MEMORY_APPROVAL_CONFIG`. It sets private file permissions and requires
an existing store configuration. It enforces local routing and
FastEmbed, leaving search mode to Basic Memory. With no configured default,
Basic Memory uses hybrid search when the vector runtime is available and text
search otherwise. The launcher disables reranking, automatic updates and
Logfire and use polling-based file watching.

The native process inherits only `HOME`, `PATH`, `TMPDIR`, `LANG`, `LC_ALL`
and `LC_CTYPE` from the launcher or owner CLI. Set any additional settings the
native process needs, such as `BASIC_MEMORY_CONFIG_DIR`, in the gate
configuration's `env` object. Do not put model credentials there.

### Migrate to the official wheel

1. Keep the previous checkout revision, patched runtime and client entries
   available for rollback. With explicit owner approval, switch all direct MCP
   entries to `shared-memory-approval-gate` while still on the previous revision
   and patched runtime. Include project-local overrides and entries that use the
   old `shared-memory-mcp` launcher. Preserve the client tool permissions.
2. Restart each affected client and check its effective launcher and project
   listing. In a disposable store, verify that `bm_project` refuses project
   creation and a durable write returns an approval proposal without saving
   the note.
3. After those checks pass, update the checkout and install the official wheel
   with `uv sync --locked`. Restart the clients and repeat the checks.

For rollback, restore the previous checkout revision and patched runtime before
restoring any direct MCP entries, then restart the affected clients.

## Build embeddings for an existing store

When moving a text-only store to hybrid search, first run `uv sync --locked`
from the checkout root to replace the old semantic-disable wheel. Remove
`default_search_type` (previously `"text"`) from the store's `state/config.json` and
`BASIC_MEMORY_DEFAULT_SEARCH_TYPE` from the launcher configuration's `env`
object if set there. Leave the mode unset rather than setting it to `hybrid`
so the native text fallback still works.

Build the missing vectors from the checkout root. FastEmbed can download the
model on first use and caches it under the store's state directory by default.

```sh
BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemory/state" \
BASIC_MEMORY_FORCE_LOCAL=true \
BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER=fastembed \
BASIC_MEMORY_RERANKER_ENABLED=false \
  uv run --locked --no-sync basic-memory reindex --embeddings
```

Restart the client to pick up the new launcher settings. Use a scoped
`bm_search` without `mode` for topic recall and `mode="text"` for exact terms
or to retry a query when semantic search is unavailable. Update any existing
client instructions that require `mode="text"` for all topic queries.

## Optional dotfiles configuration

Client configuration and shared instructions can live in a personal dotfiles
repository, shown here as `/path/to/dotfiles`. Other setups do not need it. The
files are:

| File | Purpose |
| --- | --- |
| `/path/to/dotfiles/agents/AGENTS.md` | One set of recall, project-scope, source, approval and conflict instructions, already linked to both clients |
| `/path/to/dotfiles/opencode/opencode.jsonc` | Global OpenCode connection and tool permissions, linked from `~/.config/opencode/opencode.jsonc` |
| `/path/to/dotfiles/codex/shared-memory.toml` | Mergeable Codex server template; replace its absolute-path placeholder before use |
| `$CODEX_HOME/config.toml`, normally `~/.codex/config.toml` | Actual Codex connection, merged without replacing unrelated machine settings |

OpenCode expands `{env:HOME}` in the checked-in launcher command using its
[configuration substitution](https://opencode.ai/docs/config/#env-vars).
Codex receives the resolved absolute launcher path. Its server is optional
(`required=false`) so memory startup failure does not block other work; tool
approval mode remains `approve`, preserving the existing client behavior.
Configure those entries to use the gate, which requires terminal approval for
durable writes.

Existing dotfiles edits were preserved. `bin/link-dotfiles opencode codex`
confirmed the existing links. Previous client configurations and dotfiles source
files are retained under `.state/client-setup/backup-20261117T170647.993230Z/` in
this checkout, including a target manifest. No commit was created in either repo.
Memory content, SQLite state and model caches stay outside the dotfiles repository and Git;
the complete machine-specific Codex config remains untracked there.

## Tool surface and instructions

Both clients expose exactly these Basic Memory tools for ordinary sessions:
`bm_project`, `bm_search`, `bm_read`, `bm_write`. Native checksum-conditional
updates use `bm_write`; delete and other native tools are not exposed.
OpenCode retains its wildcard deny and allows only these four exceptions;
unrelated installation permissions and security policies are preserved.
Ordinary coding tools remain available. The ignored project configurations
were updated too, preventing the old read-only corpus connection from overriding
the new global connection in this checkout. Historical evaluation templates
remain available separately and must be applied deliberately for isolated runs.

The shared instructions require project discovery, personal plus current-project
recall at startup and as new topics arise, explicit active scopes, reading
relevant hits, sources and conflict reporting, and visible nonblocking outages.
Topic queries use hybrid search and exact lookups use text search.
Durable findings and preferences require presenting concrete content and receiving
explicit owner approval before saving. Temporary saves need no individual approval.
The gate enforces terminal approval on its MCP write path.
Seven-day inactivity and archive rules are caller responsibilities. The
[verified lifecycle addition](archive/temporary-context.md) is now activated in the
shared AGENTS file.

## Verification on 17 November 2026

The connection check used actual installed clients, their global configuration,
and temporary active notes in both external projects. The clients used model
calls for verification and the memory service ran in text-only mode.
No MCP configuration was injected through CLI overrides or
`OPENCODE_CONFIG_CONTENT`. Codex used fresh ephemeral threads; OpenCode used its
normal `build` agent with a private local server and an existing available model.
A temporary capture-only OpenCode plugin recorded outgoing tool names and shared
instructions without editing them, and was removed after the check.

The first run, `.state/client-setup/20261117T170853.031016Z-verify/`, confirmed
successful retrieval and the four-tool inventories but observed OpenCode using
`all_projects=true`. The shared instructions were made concrete: ordinary
`bm_search` calls must use `projects=["personal", "<current-project>"]`,
`mode="text"` and `filters={"status":"active"}`, with `all_projects=true`
explicitly excluded. This is why connection success alone was insufficient.

The repeat run is retained under
`.state/client-setup/20261117T171247.772384Z-verify/`. Both clients discovered
projects, searched and read the temporary notes in response to an ordinary status
question without a reminder to consult memory. OpenCode's request inventory
contained the four permitted memory tools alongside its normal coding tools;
the shared instructions were present. Codex's live `mcpServerStatus/list` returned
exactly those four tools in both this checkout and the dotfiles checkout. The
historical corpus was unchanged and the temporary notes were removed using native
checksum-guarded deletion.

A separate OpenCode global check from the dotfiles checkout, with no project-local
MCP override, verified the expanded launcher path and a connected live MCP server.
Evidence is retained alongside the first run in `opencode-global-*.json` and the
global readiness transcript. The dotfiles repository's existing permission and linking checks
passed: 73 tests and 131 subtests. The launcher passed `bash -n`.

These initial checks establish connection, actual tool exposure and startup
recall. The remaining behavior checks are recorded below. Existing concurrency
checks remain supporting evidence for native conditional writes; no productive
durable knowledge or preferences were saved by these checks.

## Shared behavior verification on 17 November 2026

The targeted follow-up used Codex's normal app-server threads and OpenCode's
normal `build` agent, retaining their installed shared instructions and coding
tools. Only the MCP server command and environment were overridden to route
memory operations to disposable native stores under
`evaluation/clients/runs/`; the productive store and client configuration were
not changed. Both stores used `semantic_search_enabled=false`. These checks
complement the earlier checks against the actual external store rather than
replacing them.

The passing multi-turn run is
`evaluation/clients/runs/20261117T172642.425850Z/`. Both clients:

- Responded to a new topic in the same session by discovering projects, searching
  `personal` plus this project with explicit text mode and active status, and
  reading the matching note. Each returned its independently generated random
  recovery token and cited the source, without a prompt to search memory.
- Presented a concrete durable project note with its conversation source and
  saved nothing in that turn. After a separate explicit chat approval, each
  created the durable, active note in its disposable project.
- Saved a temporary active handover with UTC `last_activity` without another
  approval request. OpenCode corrected its handover using the native checksum.
  This verifies capture only; expiry, archive and cross-session resumption remain
  part of the dedicated lifecycle task.

The first exploratory run (`20261117T172519.006616Z`) used “Merke dir dauerhaft”
as its supposed unapproved turn. Codex treated that direct save instruction as
authorization and wrote immediately. The repeat instead asked for a proposed
note, followed by a separate approval. The passing result demonstrates that
proposal/approval conversation, not a technical write barrier or a guarantee for
every wording; explicit user instructions can authorize writes.

The outage follow-up is
`evaluation/clients/runs/20261117T173357.940087Z/`. The server command was replaced
with `/usr/bin/false`, without disabling ordinary coding tools or making the
server required. Both clients reported that they could not retrieve the recovery
token because memory tools were unavailable, and still answered the independent
calculation with `391`. Their actual responses were inspected, in addition to
checking successful turn completion. A preliminary arithmetic-only outage turn
returned `391` without a memory warning in both clients: visible reporting is
verified when missing memory context is relevant, not as an unconditional banner
for every trivial prompt.

Reproduce with the installed clients and their existing model credentials:

```sh
uv run --locked --no-sync python evaluation/clients/behavior.py
```

The probe installs nothing, leaves its disposable stores and raw transcripts in
the run directory, and requires inspection of the proposal and outage responses.
It checks retrieval arguments and the unpredictable token, write-call ordering,
saved durable content, temporary metadata and successful independent work during
outage. Client runtime logs/session state use their normal locations.

Restart existing Codex and OpenCode sessions to load the updated configuration
and instructions. The verification servers have stopped; future client sessions
start the same service on demand. Existing sessions can retain their old MCP
connection and tool catalog until restarted.
