# Shared memory architecture roadmap

Move to the official Basic Memory 1.0.0 package and enforce project creation
policy at the MCP proxy. Keep Basic Memory as the search and indexing engine.
Markdown and independently readable OKF exports provide a path to another
backend if one is needed later.

## Migration to the official runtime

The custom wheel blocked `bm_project(command="create")` by default. In upstream
1.0.0, `list`, `recent` and `create` share the same tool. The approval gate
enforces the rule for both launcher names.
[Historical patch](../patches/README.md) · [Gate](../shared_memory/approval_gate/proxy.py#L163) ·
[Upstream project tool](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/mcp/tools/projects.py)

- [x] **Use one approval path.** Route both launcher names through the terminal
  approval gate. Keep project creation in the operator CLI via
  `basic-memory project add`.
- [x] **Switch the checkout to the upstream wheel.** Pin the official
  `basic-memory==1.0.0` from PyPI and remove the custom build, patch and
  patch-only checks. [Package and launcher definitions](../pyproject.toml) ·
  [Current launchers](client-connections.md#launchers)
- [x] **Verify the official runtime in disposable stores.** Both launcher
  names allowed discovery and recent activity and refused MCP project
  creation. The operator CLI created the project successfully. The integration
  suite verified reads, temporary writes, terminal approval, watcher indexing
  and text fallback against the official wheel.
- [ ] **Roll out with owner approval.** Switch and verify all direct MCP entries,
  including project-local overrides, before installing the official wheel.
  Keep the previous launcher configuration and runtime for rollback.
  [Approval policy](adr/0013-technical-approval-for-durable-writes.md) ·
  [Migration procedure](client-connections.md#migrate-to-the-official-wheel)

## Recovery and export backlog

- [x] **Define recovery for the approval gate.** Snapshots include
  `approval-audit.jsonl` and `approvals/` from the store root. Restore retains
  the audit trail, closes pending proposals as `closed_by_recovery`, and leaves `applying` and
  `outcome_unknown` unapprovable, so no proposal can be replayed automatically.
  The isolated recovery test verifies the retained evidence and the refusal of
  both a closed and an uncertain proposal.
  [Recovery decision](adr/0015-recovery-retains-approval-evidence.md) ·
  [Backup procedure](productive-backup.md#approval-state) ·
  [Recovery tests](../tests/shared_memory/ops/test_recovery_integration.py)
- [ ] **Publish the complete OKF export together.** A failure in the second
  project left the first bundle under the final path and blocked a retry to the
  same destination. Stage all bundles beside the destination and publish only
  when every project succeeds. Test failure in the second project and retry to
  the same destination. [Export loop](../shared_memory/ops/portable_export.py#L30)

## Verify productive hybrid search

- [x] **Verify semantic recall through MCP.** On the official wheel and a
  disposable store, a paraphrase without shared keywords retrieved the expected
  note with `mode` unset. The same query in text mode returned no results. The
  watcher probe continues to cover operation without the vector runtime.
  [Search decision](adr/0014-native-local-embeddings.md) ·
  [Text scorer](../evaluation/recall/score.py#L21) ·
  [Fallback probe](../evaluation/native/mcp_watcher.py#L215)

Run the semantic check with a populated FastEmbed model cache.

```sh
SHARED_MEMORY_TEST_FASTEMBED_CACHE=/path/to/model-cache \
  uv run --locked --no-sync pytest tests/shared_memory/approval_gate/test_native_integration.py \
  -k default_hybrid_search
```
