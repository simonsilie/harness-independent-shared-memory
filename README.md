# Harness-independent shared memory

Share project notes, personal preferences and work handovers between Codex,
OpenCode and Claude Code. All three connect to the same local
[Basic Memory](https://github.com/basicmachines-co/basic-memory) store over MCP,
so a session can pick up where another left off. Other coding agents can connect
to the same store if they support local MCP servers over stdio. Notes are
Markdown, and SQLite indexes them for text search. The repository includes the
runtime build, backup and restore commands, and portable export.

We patch Basic Memory so that [storage and text search work without an AI model
or external AI service](docs/adr/0007-model-independent-storage-and-text-search.md).
A second patch lets agents discover existing projects over MCP while reserving
[project creation](patches/README.md#mcp-project-creation) for the operator by
default.

## Quick start

From a fresh checkout on macOS or Linux, sync the locked environment with `uv`.
The checkout selects Python 3.14. Both `uv sync` and `uv run` use the patched
Basic Memory wheel from the lockfile.

```sh
uv sync --locked
```

Run a command with `--help` to see its environment variables. For example,
`SHARED_MEMORY_RUNTIME_OUT=build/dist uv run --locked python build/semantic_runtime.py build`
sets the output directory. Command-line arguments take precedence.
`LOGURU_LEVEL` controls which status messages appear on stderr.

Run the setup script from the repository root to create a private
`~/SharedMemory` with separate directories for personal defaults and an example
project. The script stops if the store already exists.

```sh
./init-store.sh
```

### Connect your coding agent

The [approval gate](docs/adr/0013-technical-approval-for-durable-writes.md) is
optional. It guards against unintended durable writes through MCP by requiring
the owner to review and confirm each proposal in a terminal. A direct Basic
Memory connection keeps approval in chat for a simpler workflow.

To set up the gate, copy the configuration template from the repository root.

```sh
cp approval_gate/config.example.json approval_gate/config.json
```

Replace the placeholder paths in that file with absolute paths to your checkout
and store. The proxy and the owner CLI share this configuration, including
`BASIC_MEMORY_CONFIG_DIR`. The launcher uses the environment created by
`uv sync --locked` during setup.

The [patched runtime](patches/README.md#mcp-project-creation) keeps `bm_project`
available for `list` and `recent` while blocking project creation by default.
Use `basic-memory project add` to add projects manually.

#### Generate Codex and OpenCode snippets

From the checkout root, print the snippet for the client you want to configure:

```sh
uv run --locked --no-sync python -m approval_gate.snippet \
  --client codex --config approval_gate/config.json

uv run --locked --no-sync python -m approval_gate.snippet \
  --client opencode --config approval_gate/config.json
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
    python -m approval_gate.proxy --config "/path/to/checkout/approval_gate/config.json"
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
`example` with `bm_project`. With the gate enabled, ask one client to propose a
short durable test note in `example`. Run the command returned with the proposal
in your own terminal, review the note and confirm it there. Then ask another
client to find it. For daily use, give clients the same instructions for
project-scoped recall, presenting durable-write proposals, checksum-protected
updates and temporary handovers.

To connect directly, use the template's `native_command` and `env` as the
client command and environment and keep the same client tool permissions.
For launchers kept in a dotfiles repository, see
[how to select the launcher](docs/client-connections.md#optional-dotfiles-launchers).
