# Claude Code setup and recall run

Run `uv sync --locked` from the repository root and sign in to Claude Code before configuring a client.

## Global access for the practical trial

First merge the `permissions.allow` and `permissions.deny` arrays from the [project settings](../evaluation/claude/settings.json) into `~/.claude/settings.json`, preserving existing settings and rules. These allow search/read and deny the other ten tools registered by Basic Memory 1.0.0. This is an explicit deny list: re-verify the effective inventory after an engine update because new tools are not automatically covered.

Register the server in user scope, replacing the launcher path with this checkout's absolute path:

```sh
claude mcp add --scope user --transport stdio basic_memory \
  --env HF_HUB_OFFLINE=1 -- /absolute/path/to/harness-independent-shared-memory/evaluation/bm mcp --project main
```

This writes the registration to `~/.claude.json` for access across repositories. Put the server name before the variadic `--env` option so it is not parsed as an environment variable. The launcher keeps the pool and engine state in the memory checkout regardless of the active repository. Leave the project-local evaluation settings in place.

Start a new session in another repository and verify the server is connected and its only exposed tools are `mcp__basic_memory__bm_search` and `mcp__basic_memory__bm_read`. Keep ordinary coding tools enabled. A `UserPromptSubmit` hook that exits 2 can capture the headless `system/init` inventory without a model request; the global check retained normal settings sources and did not inject an MCP server configuration or CLI permission overrides.

The installed Claude Code 2.1.311 reported the global server as `pending` at the first blocked prompt. Repeating the check with the temporary environment variable `CLAUDE_CODE_MCP_STARTUP_WAIT_MS=120000` produced a connected inventory with exactly the two allowed Basic Memory tools. This variable was verified against the installed executable and was not added to global settings. Do not count a `pending` inventory as a failed connection or as verification of the restrictions; allow startup to finish and check again. Ordinary first-turn retrieval reliability remains part of the trial.

## Isolated recall evaluation

Run these steps from the memory project root. The runner supplies `evaluation/claude/mcp.json` and project permissions explicitly while disabling other settings sources; its inventory check does not verify global scope.

1. Check the installed versions:

   ```sh
   claude --version
   ./evaluation/bm --version
   ```

2. Copy the [MCP configuration template](../evaluation/claude/mcp.example.json) into your ignored local configuration:

   ```sh
   cp evaluation/claude/mcp.example.json evaluation/claude/mcp.json
   ```

   Set `command` in `evaluation/claude/mcp.json` to the absolute path of this checkout's `evaluation/bm` launcher; update it if the checkout moves. Keep an existing local configuration instead of copying over it. The server runs `bm mcp --project main` with `HF_HUB_OFFLINE=1`. Claude Code has no per-server tool allowlist, so the tracked [project settings](../evaluation/claude/settings.json) allow `bm_search` and `bm_read` and deny the ten other tools Basic Memory 1.0.0 registers; denied tools are removed from the model's tool list. A new engine tool is not covered by the deny list, so the inventory check below fails instead of exposing it.

3. Verify the live client inventory before using it:

   ```sh
   uv run --locked python evaluation/claude/run.py --verify-only
   ```

   The runner starts `claude --print` in an empty evaluation workspace with only `evaluation/claude/mcp.json` (`--strict-mcp-config`) and the project settings (`--setting-sources ""`), all built-in tools removed (`--tools ""`), `dontAsk` permissions, slash commands, CLAUDE.md files and auto-memory disabled, and no session persistence. For the inventory check, a `UserPromptSubmit` hook blocks the prompt, so Claude Code reports its live `init` inventory without a model request. The runner requires exactly `mcp__basic_memory__bm_search` and `mcp__basic_memory__bm_read` and a connected server, and saves them to `effective-tools.json`.

4. Run all 22 unchanged questions:

   ```sh
   uv run --locked python evaluation/claude/run.py
   ```

   This repeats the inventory check on the evaluated session's own `init` event. The prompt matches the Codex prompt and contains the contents of `evaluation/questions.json`; neither `evaluation/recall/prepare.py` nor the answer key is supplied or indexed. The model is the account default, recorded in `effective-tools.json`. Raw stream events, including every tool call and result, are retained in `events.jsonl`. This is workflow isolation under a trusted owner, not an OS confidentiality boundary.

5. Verify the response against actual tool calls, then score it. Replace `RUN_DIRECTORY` with the directory printed by the runner:

   ```sh
   uv run --locked python evaluation/claude/verify.py RUN_DIRECTORY
   uv run --locked python -m evaluation.recall.score evaluation/results-claude.json
   ```

   Verification checks the inventory, that only the two allowed tools ran without errors or permission denials, all 22 actual search modes, returned ID order including irrelevant hits, source revisions of notes read, and unchanged corpus bytes. It writes `evaluation/results-claude.json` and keeps `results.json` and `tool-calls.json` in the run directory.

6. Test startup retrieval without a memory reminder, and startup outage behaviour:

   ```sh
   uv run --locked python evaluation/claude/run.py --startup
   uv run --locked python evaluation/claude/verify.py RUN_DIRECTORY --startup
   uv run --locked python evaluation/claude/run.py --outage
   ```

   The startup run uses the Codex startup task and instructions, which do not mention memory or retrieval; verification requires a search returning and a read of `memory-20` at the current source revision and writes `startup-result.json`. The outage run substitutes `/usr/bin/false` for the server command in the run's copy of the configuration and stops before a model request. Claude Code has no required-server setting: it reports the server as `failed` with no memory tools and would continue the session without them.

Recorded checks are documented in [evaluation results](evaluation-results.md).
