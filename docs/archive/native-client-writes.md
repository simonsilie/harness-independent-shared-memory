# Native conditional writes through Codex and OpenCode

This targeted check covers [ADR 0008](../adr/0008-concurrent-sessions-with-conflict-detection.md)
using native `bm_read` and `bm_write`, without the workflow facade or a separate
reviewer identity. Writes are authorized only to disposable fixture notes.

## Result: passed on 17 November 2026

Basic Memory 1.0.0, Codex CLI 0.169.0 and OpenCode 2.3.0 passed all six client
turns in `evaluation/phase1b/runs/20261117T154059.886613Z-native-writes/`.
Both clients created and read notes, performed checksum-conditional updates,
and received `REVISION_CONFLICT` for their stale writes. Both winning bodies,
checksums, database versions and Markdown files survived both rejected writes.
All six native server guards recorded no outbound connections or inference
imports; only the intentional `sqlite_vec` rejection occurred. No model files
were downloaded, and the historical corpus bytes remained unchanged.

The Codex turns each use a fresh ephemeral session. OpenCode starts a private
server and a fresh operation session per turn. This verifies stale checksums
across sessions without relying on chat history to recover them.

## Reproduction and contract

```sh
uv run --locked --no-sync python evaluation/native/native_client_writes.py
```

The probe uses the installed clients and credentials for ordinary model turns.
It does not install software or replace client configuration. Codex receives
disposable CLI configuration; OpenCode receives `OPENCODE_CONFIG_CONTENT` and a
private local server. Its readiness turn opens the checkout location before the
explicit MCP connection, following the existing OpenCode harness convention.

Both clients access one disposable native Basic Memory SQLite store. Codex
creates and reads note A; OpenCode creates and reads note B and reads A. Codex
reads B and updates A using A's original checksum. OpenCode updates B using B's
original checksum. Each client then attempts to overwrite the other client's
newer revision using its previously read checksum. Both stale writes must
return `REVISION_CONFLICT` without a retry or refreshed checksum. After each
rejection, both native database contents/checksums/versions and Markdown files
must equal the winning snapshot. The historical corpus must remain unchanged.

This tests stale state across independent client sessions, not simultaneous
arrival at the database lock. The prior native CLI and concurrency probes
remain supporting evidence for transaction behavior; they are not rerun here.

## Configuration limitation

The native MCP subprocesses use the existing inference/network guard and its
simulated missing-`sqlite_vec` fallback. Client model requests remain enabled.
Consequently, a passing conditional-write result establishes the native client
contract only; it does not resolve the [global model-free configuration
gap](model-free-operation.md), deploy a productive store, or install durable
write approval instructions.

Run directories under `evaluation/phase1b/runs/*-native-writes/` retain prompts,
client versions, raw client events, parsed native tool calls, guards and the
disposable store. Only a run reaching `result.json` counts as a passing check.
