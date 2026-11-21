# Harness-independent shared memory

Share project notes, personal preferences and work handovers between Codex,
OpenCode and Claude Code. All three connect to the same local Basic Memory
store over MCP, so a session can pick up where another left off. Other coding
agents can connect to the same store if they support local MCP servers over
stdio. Notes are Markdown, SQLite indexes them for text search, and the patched
runtime runs without an embedding model. The repository includes the runtime
build, backup and restore commands, and portable export.

## Quick start

From a fresh checkout on macOS or Linux, use `uv` and `patch` to build and
install the patched Basic Memory wheel. The checkout selects Python 3.14. Use
the installed `basic-memory` executable directly afterward so a dependency
sync does not replace the patch.

```sh
uv sync --locked
uv run --locked --no-sync python build/semantic_runtime.py build
uv pip install --python .venv/bin/python --no-deps \
  build/dist/basic_memory-1.0.0+semantic.1-py3-none-any.whl
```

Run the setup script from the repository root to create a private
`~/SharedMemory` with separate directories for personal defaults and an example
project. The script stops if the store already exists.

```sh
./init-store.sh
```

### Connect your coding agent

Merge the server entry into each client's existing configuration. Replace the
example paths with absolute paths to your checkout and store.

The [patched runtime](patches/README.md#mcp-project-creation) keeps `bm_project`
available for `list` and `recent` while blocking project creation by default.
Use `basic-memory project add` to add projects manually.

**Codex** · `~/.codex/config.toml`

```toml
[mcp_servers.basic_memory]
command = "/path/to/checkout/.venv/bin/basic-memory"
args = ["mcp", "--transport", "stdio"]
enabled_tools = ["bm_project", "bm_search", "bm_read", "bm_write"]

[mcp_servers.basic_memory.env]
BASIC_MEMORY_CONFIG_DIR = "/path/to/SharedMemory/state"
BASIC_MEMORY_FORCE_LOCAL = "true"
FASTMCP_CHECK_FOR_UPDATES = "off"
WATCHFILES_FORCE_POLLING = "true"
```

**OpenCode** · `~/.config/opencode/opencode.jsonc`

```json
{
  "mcp": {
    "servers": {
      "basic_memory": {
        "type": "local",
        "command": ["/path/to/checkout/.venv/bin/basic-memory", "mcp", "--transport", "stdio"],
        "codemode": false,
        "environment": {
          "BASIC_MEMORY_CONFIG_DIR": "/path/to/SharedMemory/state",
          "BASIC_MEMORY_FORCE_LOCAL": "true",
          "FASTMCP_CHECK_FOR_UPDATES": "off",
          "WATCHFILES_FORCE_POLLING": "true"
        }
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

Register the server in user scope so you can use it across repositories.

```sh
claude mcp add --scope user --transport stdio basic_memory \
  --env BASIC_MEMORY_CONFIG_DIR="/path/to/SharedMemory/state" \
    BASIC_MEMORY_FORCE_LOCAL=true FASTMCP_CHECK_FOR_UPDATES=off WATCHFILES_FORCE_POLLING=true \
  -- "/path/to/checkout/.venv/bin/basic-memory" mcp --transport stdio
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

Start fresh sessions and check that each configured client lists `personal` and `example`
with `bm_project`. To try cross-client recall, approve a short test note in
`example` in one client and ask another to find it. For daily use, give your
clients the same instructions for project-scoped recall, explicit approval of
durable notes, checksum-protected updates and temporary handovers. The approval
rule is a client workflow convention.
