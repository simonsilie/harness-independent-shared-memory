# Harness-independent shared memory

Keep project decisions, personal preferences and work handovers available when
you switch between Codex, OpenCode and Claude Code. This setup is for one
developer working across sessions and repositories on the same machine. You can
leave a handover with the next step in Codex and pick it up in OpenCode. Other
coding agents can connect if they support local MCP servers over stdio.

## What this adds to Basic Memory

Basic Memory already provides local Markdown notes, SQLite full-text search
and access from multiple MCP clients. Its hybrid search combines keyword
matches with embeddings generated locally by FastEmbed.
[Basic Memory overview](https://docs.basicmemory.com/start-here/what-is-basic-memory)

- **Project-scoped recall and handovers.** Shared client instructions keep
  personal preferences and project decisions separate from unfinished work.
  Agents search `personal` and the current project and manage the seven-day
  inactivity window and archive for handovers. Topic queries use hybrid search
  and exact lookups use text search.
  [Client instructions](docs/client-connections.md#tool-surface-and-instructions) ·
  [Handover lifecycle](docs/shared-memory-lifecycle.md)
- **Terminal approval.** The MCP gate sends durable writes to the owner
  for review and confirmation, while eligible temporary handovers can be saved
  directly. The gate guards its MCP write path. Its protection depends on the
  client's shell and filesystem permissions.
  [Approval policy](docs/adr/0013-technical-approval-for-durable-writes.md)
- **Store snapshots and portable export.** `memory-ops` validates snapshots of
  the notes, SQLite database and store configuration for same-version recovery.
  It also runs Basic Memory's OKF export for every configured project. The
  exported Markdown and YAML can be read independently.
  [Backup and restore](docs/productive-backup.md) ·
  [Portable export](docs/portable-export.md)

## Quick start

From a fresh checkout on macOS or Linux, sync the locked environment with `uv`.
The checkout selects Python 3.14 and pins the official Basic Memory release.

```sh
uv sync --locked
```

Run a command with `--help` to see its environment variables. Command-line
arguments take precedence.
`LOGURU_LEVEL` controls which status messages appear on stderr.

Run the setup script from the repository root to create a private
`~/SharedMemory` with separate directories for personal defaults and an example
project. The script stops if the store already exists.

```sh
./init-store.sh
```

For an existing store, [build embeddings for existing notes](docs/client-connections.md#build-embeddings-for-an-existing-store).

### Connect your coding agent

Copy the configuration template from the repository root if you have no local
configuration yet.

```sh
cp shared_memory/approval_gate/config.example.json shared_memory/approval_gate/config.json
```

Replace the placeholder paths in that file with absolute paths to your checkout
and store. The proxy and the owner CLI share this configuration, including
`BASIC_MEMORY_CONFIG_DIR`. Set `proposals_dir` to `<store-root>/approvals` and
`audit_log` to `<store-root>/approval-audit.jsonl` so `memory-ops backup` includes
them in snapshots. The launcher uses the environment created by
`uv sync --locked` during setup.

The gate keeps `bm_project` available for discovery and recent activity.
Add projects through the CLI with their notes directories under `~/SharedMemory`.

```sh
BASIC_MEMORY_CONFIG_DIR="$HOME/SharedMemory/state" BASIC_MEMORY_FORCE_LOCAL=true \
  uv run --locked --no-sync basic-memory project add my-project \
  "$HOME/SharedMemory/notes/projects/my-project"
```

#### Generate Codex and OpenCode snippets

From the checkout root, print the snippet for the client you want to configure:

```sh
uv run --locked --no-sync python -m shared_memory.approval_gate.snippet \
  --client codex --config shared_memory/approval_gate/config.json

uv run --locked --no-sync python -m shared_memory.approval_gate.snippet \
  --client opencode --config shared_memory/approval_gate/config.json
```

Merge the Codex snippet into `~/.codex/config.toml` or the OpenCode snippet into
`~/.config/opencode/opencode.jsonc`. If a local `basic_memory` entry already
exists, update `command` and `args` for Codex, or `command` and `codemode`
(`false`) for OpenCode. Keep existing tool permissions.
When adding the OpenCode defaults, put them before existing permission rules so
the existing rules take precedence.

A project-local `basic_memory` entry can override the global launcher. Check
which entry applies in the project where you will use the gate, and update that
entry if needed. After saving, restart Codex or reload OpenCode. Then
[verify the gate in a disposable project](docs/client-connections.md#configuration):
a synthetic durable write should return a proposal without creating the note
while approval is pending.

**Claude Code**

Register the server in user scope so you can use it across repositories. To
replace an existing user-scope `basic_memory` entry, remove it first with
`claude mcp remove --scope user basic_memory`.

```sh
claude mcp add --scope user --transport stdio basic_memory \
  -- "/path/to/uv" run --directory "/path/to/checkout" --locked --no-sync \
    shared-memory-approval-gate --config "/path/to/checkout/shared_memory/approval_gate/config.json"
```

To match the tool set above, merge these rules into `~/.claude/settings.json`.
Keep existing rules and check the effective tool list after updating Basic Memory.

```json
{
  "permissions": {
    "deny": [
      "mcp__basic_memory__bm_context",
      "mcp__basic_memory__bm_delete",
      "mcp__basic_memory__bm_edit",
      "mcp__basic_memory__bm_find",
      "mcp__basic_memory__bm_list",
      "mcp__basic_memory__bm_man",
      "mcp__basic_memory__bm_move",
      "mcp__basic_memory__bm_project_delete",
      "mcp__basic_memory__bm_schema"
    ]
  }
}
```

Start fresh sessions and check that each configured client lists `personal` and
`example` with `bm_project`. Ask one client to propose a
short durable test note in `example`. Run the command returned with the proposal
in your own terminal, review the note and confirm it there. Then ask another
client to find it. For daily use, give each client the
[same recall and write instructions](docs/client-connections.md#tool-surface-and-instructions)
and the [handover lifecycle rules](docs/shared-memory-lifecycle.md).

In this checkout, `shared-memory-mcp` also starts the gate. When upgrading an
existing installation, switch and verify all direct MCP entries before
installing the official wheel. [Launcher migration](docs/client-connections.md#migrate-to-the-official-wheel)

## Architecture and evaluation

The repository includes a separate read-only corpus and runners for Codex,
OpenCode and Claude Code. They verify which memory tools each client used, which
notes it retrieved and read, and whether the corpus was left intact.
[Repository architecture](docs/repository-architecture.md) ·
[Architecture roadmap](docs/roadmap.md) ·
[Recorded recall results](docs/archive/evaluation-results.md)
