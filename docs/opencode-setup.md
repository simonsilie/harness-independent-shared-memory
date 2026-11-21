# OpenCode setup and recall run

For current productive use, see [client connections](client-connections.md).
The read-only trial and evaluation instructions below are historical setups.

Run `uv sync --locked` from the repository root and sign in to OpenCode before configuring a client.

## Historical global access for the read-only trial

Merge only the `mcp` server settings from the [template](../evaluation/opencode/opencode.example.json) into `~/.config/opencode/opencode.jsonc`, preserving existing configuration. Set the command to the absolute path of this checkout's `evaluation/bm` launcher, keep `codemode: false`, `HF_HUB_OFFLINE: "1"`, and the template's timeouts. The launcher keeps the pool and engine state in the memory checkout regardless of the active repository. If the global config is a dotfiles symlink, edit its source and follow that repository's linking workflow.

Append these ordered rules to the global `permissions` array, preserving other permissions and policies:

```json
[
  { "action": "basic_memory_*", "resource": "*", "effect": "deny" },
  { "action": "basic_memory_bm_search", "resource": "*", "effect": "allow" },
  { "action": "basic_memory_bm_read", "resource": "*", "effect": "allow" }
]
```

The last matching permission wins. The wildcard denies other Basic Memory tools, including new tool names, while the two exceptions permit retrieval. Agent-specific rules can override these permissions, so verify the live inventory for the agents used during the trial. Keep the evaluation agents and capture plugin project-local; they remove ordinary coding tools and are unsuitable for everyday sessions.

Start a fresh session in another repository and confirm the server is connected and its only exposed tools are `basic_memory_bm_search` and `basic_memory_bm_read`, with ordinary coding tools still available. Check the effective request inventory without stripping tools during verification. The recorded global check used a temporary capture-only context hook that stopped before provider invocation. These are client workflow restrictions, not a server-side read-only boundary.

## Isolated recall evaluation

Run these steps from the memory project root. The runner loads `evaluation/opencode/opencode.json` and the capture plugin through an inline configuration override; its inventory check does not verify global access from another checkout.

1. Check the installed versions:

   ```sh
   opencode --version
   ./evaluation/bm --version
   ```

2. Copy the [OpenCode configuration template](../evaluation/opencode/opencode.example.json) into your ignored local configuration:

   ```sh
   cp evaluation/opencode/opencode.example.json evaluation/opencode/opencode.json
   ```

   Set the absolute path of this checkout's `evaluation/bm` launcher in `mcp.servers.basic_memory.command`; update it if the checkout moves. Keep an existing local configuration instead of copying over it. The server runs `bm mcp --project main` with `codemode: false`, `HF_HUB_OFFLINE: "1"` in the server environment, and 120-second startup/execution timeouts. OpenCode has no per-server tool allowlist, so the search/read-only restriction is enforced on the client: the `memory-eval` and `memory-startup` agents in the template deny every action except `basic_memory_bm_search` and `basic_memory_bm_read`, and the project-local [evaluation plugin](../evaluation/opencode/eval-capture/index.ts) removes every other tool — built-in filesystem, shell, web, and skill tools included — from the outgoing model request. The plugin is an evaluation-harness restriction under a trusted owner, not an engine capability or an OS boundary.

3. Verify the live client inventory before using it:

   ```sh
   uv run --locked python evaluation/opencode/run.py --verify-only
   ```

   The runner starts a private local OpenCode server and a fresh session with the `memory-eval` agent. It sends only harmless readiness prompts while initializing and connecting MCP. The plugin records the live tool inventory, MCP connection status, and system prompt, then stops the request before model invocation. The runner independently checks that exactly `bm_search` and `bm_read` are available, the server is connected, and the system prompt references no evaluation materials. Missing capture or an invalid inventory stops evaluation. `--verify-only` exits after this check without sending questions.

4. Run all 22 unchanged questions:

   ```sh
   uv run --locked python evaluation/opencode/run.py
   ```

   Each run verifies inventory as above, then continues the same fresh session through `opencode run` against that private server with the model pinned to `opencode-go/glm-5.3-flash`; the service default resolved to an OpenRouter model whose credits were exhausted, and the failed first attempts are retained in the runs directory. The prompt contains only the contents of `evaluation/questions.json`; the evaluation instructions live in the agent definition and are recorded in the run evidence. Neither `evaluation/recall/prepare.py` nor the answer key is supplied or indexed. The client chooses one keyword query per question, explicitly passes `mode="text"`, `page_size=5`, `output_format="json"`, and `project="main"`, and reads returned notes when it decides evidence must be inspected. Raw client events, tool arguments, results, and timestamps are retained. The plugin stops requests if session identity cannot be resolved or evidence cannot be recorded. Unlike Codex, the evaluated session runs in the real checkout; file, shell, web, and other tools are denied, so it cannot read local materials. OpenCode's session records live in the shared service data directory outside the project; the raw evidence copies are project-local.

5. Verify the response against actual tool calls, then score it after the client exits. Replace `RUN_DIRECTORY` with the directory printed by the runner:

   ```sh
   uv run --locked python evaluation/opencode/verify.py RUN_DIRECTORY
   uv run --locked python -m evaluation.recall.score evaluation/results-opencode.json
   ```

   Verification checks the effective tool inventory from the live session snapshot, all 22 actual search modes, returned ID order including irrelevant hits, source revisions for notes actually read, unchanged corpus bytes, and that the declared results match the actual calls query by query. Search permalinks are mapped against local corpus metadata; that alone does not verify the source revision served by the engine. `verification-summary.json` lists returned note IDs lacking read-based source-revision verification, separately from the recall score. It writes `results-opencode.json`, plus `results.json` and `tool-calls.json` in that run directory. Each invocation gets a separate timestamped directory so reruns preserve earlier evidence.

6. Test startup retrieval without a memory reminder:

   ```sh
   uv run --locked python evaluation/opencode/run.py --startup
   uv run --locked python evaluation/opencode/verify_startup.py RUN_DIRECTORY
   ```

   The startup run uses the `memory-startup` agent, whose instructions do not mention memory or retrieval, and asserts the prompt itself contains no such mention. `verify_startup.py` requires paired successful searches and reads, including retrieval and a read of the accepted SQLite safety note at the current source revision. It checks that neither the prompt nor the captured agent instructions mention memory retrieval, and records the effective inventory, executed tools, and response in `startup-result.json`; corpus hashes remain in the run directory.

Recorded recall and startup checks are documented in [evaluation results](evaluation-results.md).
