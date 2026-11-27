# Productive Codex and OpenCode connections

The client launchers use the native Basic Memory service and the external store
at `$HOME/SharedMemory`. The historical corpus remains separate.

## Configuration

This checkout is all a client connection needs. Follow the
[quick start](../README.md#quick-start): run `uv sync --locked`, create the
store with `./init-store.sh`, copy `approval_gate/config.example.json` to
`approval_gate/config.json` and generate each client's entry with the
[snippet generator](../README.md#generate-codex-and-opencode-snippets). For a
direct connection without the gate, use the template's `native_command` and
`env` as the client command and environment. Verify the proxy against
disposable stores with
`uv run --locked --no-sync pytest -m integration tests/approval_gate`.

Check the effective server entry, including any project-local override, to see
which command a client will use. Switching productive clients between the gate
and a direct connection requires explicit owner approval. After a switch,
restart each affected client and check that `bm_project` with `command="list"`
returns the expected projects. To verify the gate, propose a synthetic durable
note in a disposable project. Check that the client receives a proposal and the
note is absent while approval is pending.

## Optional dotfiles launchers

Launchers and shared client instructions can live in a personal dotfiles
repository, shown here as `/path/to/dotfiles`. Other setups do not need it. The
files are:

| File | Purpose |
| --- | --- |
| `/path/to/dotfiles/bin/shared-memory-mcp` | Shared launcher for the patched project environment and external configuration |
| `/path/to/dotfiles/agents/AGENTS.md` | One set of recall, project-scope, source, approval and conflict instructions, already linked to both clients |
| `/path/to/dotfiles/opencode/opencode.jsonc` | Global OpenCode connection and tool permissions, linked from `~/.config/opencode/opencode.jsonc` |
| `/path/to/dotfiles/codex/shared-memory.toml` | Mergeable Codex server template; replace its absolute-path placeholder before use |
| `$CODEX_HOME/config.toml`, normally `~/.codex/config.toml` | Actual Codex connection, merged without replacing unrelated machine settings |

The launcher uses `$HOME/Projects/harness-independent-shared-memory/.venv` and
`$HOME/SharedMemory/state`. It requires the installed semantic-disable patch and
refuses an unpatched runtime before native startup. It forces local routing,
semantic search off, automatic updates and Logfire off, polling-based file
watching and private file permissions. Moving the checkout requires adjusting
the launcher.

Dotfiles repositories with `bin/shared-memory-approval-gate` and
`shared-memory/approval-gate.json` can use the
[durable-write approval gate](adr/0013-technical-approval-for-durable-writes.md).
The gate uses the same environment and runs `bin/shared-memory-mcp` as its
native server.

With explicit owner approval, select the launcher in each client's
`basic_memory` server entry. Use `bin/shared-memory-approval-gate` for terminal
approval or `bin/shared-memory-mcp` for chat approval. Supply the absolute dotfiles
path in Codex and use the existing `{env:HOME}` substitution in OpenCode. The
dotfiles wrappers take no MCP arguments from the client. Preserve the client tool
permissions, restart each affected client and verify it as described above. To
restore the previous mode, select its launcher again and restart the client.

OpenCode expands `{env:HOME}` in the checked-in launcher command using its
[configuration substitution](https://opencode.ai/docs/config/#env-vars).
Codex receives the resolved absolute launcher path. Its server is optional
(`required=false`) so memory startup failure does not block other work; tool
approval mode remains `approve`, preserving the existing client behavior.
Direct connections apply the chat convention described below. Connections through
the gate require terminal approval for durable writes.

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
text recall at startup and as new topics arise, explicit active scopes, reading
relevant hits, sources and conflict reporting, and visible nonblocking outages.
Durable findings and preferences require presenting concrete content and receiving
explicit owner approval before saving. Temporary saves need no individual approval.
The gate enforces terminal approval on its MCP write path.
Seven-day inactivity and archive rules are caller responsibilities. The
[verified lifecycle addition](temporary-context.md) is now activated in the
shared AGENTS file.

## Verification on 17 November 2026

The connection check used actual installed clients, their global configuration,
and temporary active notes in both external projects. Model calls were allowed
for client verification; the memory service itself uses the model-free runtime.
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
outage. Client runtime logs/session state use their normal locations. The shared
behavior roadmap item is complete with these workflow-level limits; this does
not close the later lifecycle, recovery or observation tasks.

Restart existing Codex and OpenCode sessions to load the updated configuration
and instructions. The verification servers have stopped; future client sessions
start the same service on demand. Existing sessions can retain their old MCP
connection and tool catalog until restarted.
