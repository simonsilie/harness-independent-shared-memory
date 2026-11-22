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
`BASIC_MEMORY_CONFIG_DIR`. Merge the server entry below into each client's
existing configuration and replace the example paths, including the absolute
path to `uv`. The launcher uses the environment created by `uv sync --locked`
during setup.

The [patched runtime](patches/README.md#mcp-project-creation) keeps `bm_project`
available for `list` and `recent` while blocking project creation by default.
Use `basic-memory project add` to add projects manually.

**Codex** · `~/.codex/config.toml`

```toml
[mcp_servers.basic_memory]
command = "/path/to/uv"
args = [
  "run", "--directory", "/path/to/checkout", "--locked", "--no-sync",
  "python", "-m", "approval_gate.proxy", "--config", "/path/to/checkout/approval_gate/config.json"
]
enabled_tools = ["bm_project", "bm_search", "bm_read", "bm_write"]
```

**OpenCode** · `~/.config/opencode/opencode.jsonc`

```json
{
  "mcp": {
    "servers": {
      "basic_memory": {
        "type": "local",
        "command": [
          "/path/to/uv", "run", "--directory", "/path/to/checkout", "--locked", "--no-sync",
          "python", "-m", "approval_gate.proxy",
          "--config", "/path/to/checkout/approval_gate/config.json"
        ],
        "codemode": false
      }
    }
  },
  "permissions": [
    { "action": "basic_memory_*", "resource": "*", "effect": "deny" },
    { "action": "basic_memory_bm_project", "resource": "*", "effect": "allow" },
    { "action": "basic_memory_bm_search", "resource": "*", "effect": "allow" },
    { "action": "basic_memory_bm_read", "resource": "*", "effect": "allow" },
    { "action": "basic_memory_bm_write", "resource": "*", "effect": "allow" }
  ]
}
```

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
`example` with `bm_project`. Ask one client to propose a short durable test note
in `example`. Run the command returned with the proposal in your own terminal,
review the note and confirm it there. Then ask another client to find it. For
daily use, give clients the same instructions for project-scoped recall,
presenting durable-write proposals, checksum-protected updates and temporary
handovers.

To connect directly, use the template's `native_command` and `env` as the
client command and environment and keep the same client tool permissions.
Existing Toolbox setups can follow the
[launcher migration instructions](docs/client-connections.md#configuration-and-ownership).
