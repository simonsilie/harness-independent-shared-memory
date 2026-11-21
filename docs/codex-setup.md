# Codex setup and recall run

For current productive use, see [client connections](client-connections.md).
The read-only trial and evaluation instructions below are historical setups.

Run `uv sync --locked` from the repository root and sign in to Codex before configuring a client.

## Historical global access for the read-only trial

Merge the server tables from the [Codex configuration template](../evaluation/codex/config.example.toml) into `~/.codex/config.toml` (or `$CODEX_HOME/config.toml` when using a custom Codex home). Preserve existing settings; do not replace the entire global file. Set `command` to the absolute path of this checkout's `evaluation/bm` launcher and update it if the checkout moves. The launcher keeps the corpus, database, and caches in the memory checkout even when Codex runs from another repository.

Keep `enabled_tools = ["bm_search", "bm_read"]`, `required = true`, both 120-second timeouts, and `HF_HUB_OFFLINE = "1"` from the template. This enables retrieval across repositories without enabling native mutation or project-management tools. With `required = true`, failure to initialize Basic Memory blocks new sessions using this configuration, including sessions in other repositories.

Start a new Codex session after changing the configuration. From a different repository, run `codex mcp list` to check configuration discovery, then inspect that session's live MCP inventory and require exactly `bm_search` and `bm_read` for `basic_memory` before using it. The list command alone does not prove that the server connected or that its effective tool restrictions hold. A project-local configuration can override global settings, so check the effective inventory in the repositories used for the trial.

Record useful recalls, misses, corrections, latency, and outages during ordinary work. Global availability is a prerequisite for the cross-repository trial, not evidence that unprompted recall is reliable. Adding new notes requires a separately authorized write workflow; this setup exposes only search and read. OpenCode and Claude Code also have global trial setups; their isolated evaluation configurations remain project-local.

## Isolated recall evaluation

Run these steps from the memory project root. The evaluation runner explicitly loads `evaluation/codex/config.toml`; its inventory check does not verify global discovery from another repository.

1. Check the installed versions:

   ```sh
   codex --version
   ./evaluation/bm --version
   ```

2. Copy the [Codex configuration template](../evaluation/codex/config.example.toml) into your ignored local configuration:

   ```sh
   cp evaluation/codex/config.example.toml evaluation/codex/config.toml
   ```

   Set `command` in `evaluation/codex/config.toml` to the absolute path of this checkout's `evaluation/bm` launcher; update it if the checkout moves. Keep an existing local configuration instead of copying over it. The server runs `bm mcp --project main` with `enabled_tools = ["bm_search", "bm_read"]`, `required = true`, and 120-second startup/tool timeouts. Codex's documented [`enabled_tools` allowlist](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) limits discovery and access. No native mutation or project-management tool is enabled.

3. Verify the live client inventory before using it:

   ```sh
   uv run --locked python evaluation/codex/run.py --verify-only
   ```

   The runner starts the installed Codex app server with the project configuration and a fresh ephemeral thread. It calls `mcpServerStatus/list` on that thread's live connection and requires exactly `bm_search` and `bm_read`; any mismatch stops the run. This checks the effective client list, not merely the configuration file or the unrestricted server catalog. The successful inventory is saved as `effective-tools.json` in the printed run directory. Startup also initializes Basic Memory's database and indexes `corpus/`.

4. Run all 22 unchanged questions:

   ```sh
   uv run --locked python evaluation/codex/run.py
   ```

   This repeats the inventory check before starting a model turn. The client receives the contents of `evaluation/questions.json` in a fresh thread rooted in an empty evaluation workspace, with shell, web, browser, apps, hooks, and delegation disabled. Neither `evaluation/recall/prepare.py` nor the answer key is supplied or indexed. The client chooses one keyword query per question, explicitly passes `mode="text"`, requests five results, and reads returned notes to check evidence. Raw requests, responses, and timestamps are retained in `events.jsonl`. This is workflow isolation under a trusted owner, not an OS confidentiality boundary.

5. Verify the response against actual tool calls, then score it after the client exits. Replace `RUN_DIRECTORY` with the directory printed by the runner:

   ```sh
   uv run --locked python evaluation/codex/verify.py RUN_DIRECTORY
   uv run --locked python -m evaluation.recall.score evaluation/results-codex.json
   ```

   Verification checks all 22 actual search modes, returned ID order including irrelevant hits, read provenance, the effective tool inventory, and unchanged corpus bytes. It writes `results-codex.json`, plus `results.json` and `tool-calls.json` in that run directory. Each invocation gets a separate timestamped directory so reruns preserve earlier evidence. Codex may need permission to start outside a restrictive process sandbox and to use its existing model-provider login; the evaluated thread remains read-only.

Recorded recall, startup, outage, recovery, and compatibility checks are documented in [evaluation results](evaluation-results.md).

## Protected real-client probe

Substitute the provisioned service account and its home directory for
`workflow-service-account` and `/path/to/service-home` in the commands below.

Historical instructions only. Run the commands in this section from the complete
archived checkout at tag `historical-workflow-20261118`
([source revision](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/docs/codex-setup.md#protected-phase-1b-real-client-probe)),
not the active tree. Productive clients use native tools, not this protected
facade; see [the retirement decision](custom-code-decision.md).

The real-client harness supports `--protected-identity`, starting with Codex,
then OpenCode and Claude Code. It exercises capture, proposal and acceptance
retries, expiry and branch eligibility, and cross-client handover through the
owner-provisioned facade. It checks protected source copies against the checkout
and consumes only service-owned artifacts bound to this run, fixture and exact
operation. It never opens the protected database or runs reviewer commands.

For the already provisioned standalone runtime described in the
[boundary results](evaluation-results.md), refresh code and start a fresh fixture
from the repository root **in your own terminal**:

```sh
runtime=/path/to/service-home/boundary-runtime
sudo mkdir -p "$runtime/code/evaluation/workflow"
sudo cp workflow/*.py "$runtime/code/workflow/"
sudo cp evaluation/workflow/boundary_service.py evaluation/workflow/boundary_checks.py \
  "$runtime/code/evaluation/workflow/"
sudo chown -R workflow-service-account "$runtime/code"
sudo chmod -R go-w "$runtime/code"

python="$runtime/venv-protected/bin/python"
runner="$runtime/code/evaluation/workflow/boundary_service.py"
fixture_id="real-clients-$(date +%Y%m%dT%H%M%S)"
fixture="/path/to/service-home/boundary/$fixture_id"
sudo -H -u workflow-service-account "$python" "$runner" setup "$fixture_id" --real-clients
sudo -H -u workflow-service-account "$python" "$runner" configure "$fixture" --port 8765
sudo -H -u workflow-service-account "$python" "$runner" serve "$fixture" --port 8765
```

Keep the facade running. Run the harness as the agent user:

```sh
uv run --locked python evaluation/workflow/real_clients.py --protected-identity
```

Execute its printed checkpoint commands in another owner terminal. Each checkpoint
waits up to 30 minutes for its trusted artifact. At `verify-final`, stop the facade
before executing the snapshot command so its guard counters are included. Raw
client transcripts, checkpoint instructions and archival artifacts remain in the
printed run directory. Only a completed run with all checks passing is evidence;
preparing the runtime or starting Codex does not establish the contract. This
probe does not cover sustained load, warmed-cache/rebuilt-index eligibility or
portable recovery and does not pass the former rollout gates by itself.

For the separate protected eligibility matrix, refresh the same runtime and use a
fresh fixture and named configuration so existing evidence stays intact. From
the repository root in the **owner terminal**:

```sh
runtime=/path/to/service-home/boundary-runtime
sudo mkdir -p "$runtime/code/evaluation/workflow"
sudo cp workflow/*.py "$runtime/code/workflow/"
sudo cp evaluation/workflow/boundary_service.py evaluation/workflow/boundary_checks.py \
  "$runtime/code/evaluation/workflow/"
sudo chown -R workflow-service-account "$runtime/code"
sudo chmod -R go-w "$runtime/code"
python="$runtime/venv-protected/bin/python"
runner="$runtime/code/evaluation/workflow/boundary_service.py"
fixture_id="eligibility-$(date +%Y%m%dT%H%M%S)"
fixture="/path/to/service-home/boundary/$fixture_id"
sudo -H -u workflow-service-account "$python" "$runner" setup "$fixture_id" --real-clients
sudo -H -u workflow-service-account "$python" "$runner" configure "$fixture" --port 8766 \
  --config-name "$fixture_id.json"
printf 'PHASE1B_BOUNDARY_CONFIG=/path/to/service-home/boundary-evidence/%s.json\n' "$fixture_id"
sudo -H -u workflow-service-account "$python" "$runner" serve "$fixture" --port 8766
```

Supply the printed configuration path to the agent. The agent runs:

```sh
PHASE1B_BOUNDARY_CONFIG=/path/to/service-home/boundary-evidence/REPLACE_WITH_PRINTED_NAME.json \
  uv run --locked python evaluation/workflow/real_clients.py --protected-identity --eligibility-lifecycle
```

Execute its owner checkpoint commands in another owner terminal. Reindexing and
reviewer operations remain there. At the restart checkpoint, stop and restart
this fixture's facade with the printed command before taking the requested
snapshot. At `verify-final`, stop it before taking the final snapshot. This
extension proves nothing until its result passes; see the [matrix and cache
limits](evaluation-results.md#protected-eligibility-probe--16-november-2026).
