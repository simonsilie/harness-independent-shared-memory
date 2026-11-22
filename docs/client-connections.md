# Productive Codex and OpenCode connections

Both clients use the native Basic Memory service and the external store at
`$HOME/SharedMemory`. The historical corpus remains separate. No workflow facade,
reviewer identity or new software dependency was introduced.

## Configuration and ownership

Reusable client behavior belongs in the toolbox repository. The active files are:

| File | Purpose |
| --- | --- |
| `$HOME/toolbox/bin/shared-memory-mcp` | Shared launcher for the patched project environment and external configuration |
| `$HOME/toolbox/dotfiles/agents/AGENTS.md` | One set of recall, project-scope, source, approval and conflict instructions, already linked to both clients |
| `$HOME/toolbox/dotfiles/opencode/opencode.jsonc` | Global OpenCode connection and tool permissions, linked from `~/.config/opencode/opencode.jsonc` |
| `$HOME/toolbox/dotfiles/codex/shared-memory.toml` | Mergeable Codex server template; replace its absolute-path placeholder before use |
| `$CODEX_HOME/config.toml`, normally `~/.codex/config.toml` | Actual Codex connection, merged without replacing unrelated machine settings |

The launcher uses `$HOME/Projects/harness-independent-shared-memory/.venv` and
`$HOME/SharedMemory/state`. It requires the installed semantic-disable patch and
refuses an unpatched runtime before native startup. It forces local routing,
semantic search off, automatic updates and Logfire off, polling-based file
watching and private file permissions. Moving the checkout requires adjusting
the launcher. Rebuild the environment with `uv sync --locked` to install the
patched wheel from the lockfile.

The Toolbox also provides `bin/shared-memory-approval-gate` and
`dotfiles/shared-memory/approval-gate.json` for the
[durable-write approval gate](adr/0013-technical-approval-for-durable-writes.md).
The gate uses the same environment and runs `bin/shared-memory-mcp` as its
native server. From the checkout, run
`.venv/bin/python approval_gate/install.py --config /path/to/approval-gate.json`.
The script reads the gate's dependency pins from `uv.lock` and
targets an existing Basic Memory environment. Pass `--wheel` to test and install
a prebuilt patched wheel in the same step. Otherwise, the installed Basic Memory
version stays in place.

Pass the approval-gate configuration directly with `--config`. For Toolbox,
this is its `dotfiles/shared-memory/approval-gate.json`. With a client that
accepts MCP arguments and environment variables, you can also run the proxy
directly. Set `PYTHONPATH` to the checkout, use the environment's Python as the
command, and pass `-m approval_gate.proxy --config /path/to/approval-gate.json`
as arguments.

To preview a deployment that switches existing launcher entries, substitute
the paths and current command values below:

```sh
checkout=/path/to/shared-memory-checkout
"$checkout/.venv/bin/python" "$checkout/approval_gate/install.py" \
  --python "$checkout/.venv/bin/python" \
  --config /path/to/approval-gate.json \
  --wheel /path/to/basic_memory-1.0.0+semantic.2-py3-none-any.whl \
  --replace-launcher /path/to/codex/config.toml \
    /path/to/shared-memory-mcp /path/to/shared-memory-approval-gate \
  --replace-launcher /path/to/opencode/opencode.jsonc \
    /path/to/shared-memory-mcp /path/to/shared-memory-approval-gate \
  --dry-run
```

Remove `--dry-run` to apply it. Each `--replace-launcher` names an existing
configuration and its exact old and new command values. Use an absolute
executable path, an OpenCode `{env:HOME}` path, or a command on both the
installer's and the client's `PATH`. Repeat it for any project-local overrides.
Before changing launcher entries, the script checks that the configured proposal
and audit paths are usable. It starts each replacement launcher without arguments
with a temporary `HOME` and a disposable project, then checks that the launcher
selects the approval-gate configuration and Python environment passed to the
installer. The replacement launcher must pass the test environment to the proxy.
Native wrappers must honor the test store settings or derive their store paths from `HOME`, as
the Toolbox launcher does. Integration tests use staged dependencies and the
candidate wheel. The installer updates the live environment after the tests pass
and repeats the launcher check with the installed packages before switching.
If updating a client configuration fails, it restores earlier launcher changes
when their files still match what it wrote.
Use `--test` to run the native integration suite when installing only the gate
dependencies. Entries that pass
arguments to the native launcher need a separate edit to remove those arguments
when switching to the proxy. Restart the clients after changing their launcher
entries.

OpenCode expands `{env:HOME}` in the checked-in launcher command using its
[configuration substitution](https://opencode.ai/docs/config/#env-vars).
Codex receives the resolved absolute launcher path. Its server is optional
(`required=false`) so memory startup failure does not block other work; tool
approval mode remains `approve`, preserving the existing client behavior.
Durable-write approval is the explicit chat convention described below.

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
These are workflow instructions, not a technical approval or access-control boundary.
Seven-day inactivity and archive rules are caller responsibilities. The
[verified lifecycle addition](temporary-context.md) is now activated in the
shared AGENTS file.

Existing toolbox edits were preserved. `bin/link-dotfiles opencode codex`
confirmed the existing links. Previous client configurations and toolbox source
files are retained under `.state/client-setup/backup-20261117T170647.993230Z/` in
this checkout, including a target manifest. No commit was created in either repo.
Memory content, SQLite state and model caches stay outside toolbox and Git;
the complete machine-specific Codex config remains untracked there.

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
exactly those four tools in both this checkout and the toolbox checkout. The
historical corpus was unchanged and the temporary notes were removed using native
checksum-guarded deletion.

A separate OpenCode global check from the toolbox checkout, with no project-local
MCP override, verified the expanded launcher path and a connected live MCP server.
Evidence is retained alongside the first run in `opencode-global-*.json` and the
global readiness transcript. The toolbox's existing permission and linking checks
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
