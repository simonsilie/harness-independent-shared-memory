---
title: Basic Memory model-independent fallback
type: note
permalink: main/pilot/basic-memory-model-independent-fallback
review_status: accepted
source_uri: ../../../evaluation/phase1b/mcp_watcher.py
source_revision: sha256:e3cf6b9beefe75cb3e4679874901f2343021ce3d9cdde5dd1df1c585a5ecb935
source_section: Probe phases (server-1 and server-2 sessions)
tags:
- basic-memory
- model-independence
- evaluation-harness
---

# Basic Memory model-independent fallback

Run Basic Memory 1.0.0 without inference by keeping sqlite-vec unavailable on
the host — there is no supported provider-off configuration value. The only
supported `semantic_embedding_provider` values are `fastembed`, `openai` and
`litellm`; any other value (including `none`) crashes at boot with
"Unsupported semantic embedding provider".

When the sqlite-vec extension is absent, the supported keyword-only fallback
covers the whole path: repository startup logs "Semantic search disabled …
Falling back to keyword-only search", the file watcher skips embedding work
entirely (zero FastEmbed imports attempted), the default search type falls back
to `text` without `BASIC_MEMORY_DEFAULT_SEARCH_TYPE`, an explicit vector/hybrid
search is refused cleanly, and `bm_write` succeeds even though its optional
similar-notes semantic probe fails. Per-note `embed: false` is not needed for
this path. Basic Memory logs go to `<config dir>/basic-memory.log`, not to the
MCP stderr stream.

In `harness-independent-shared-memory`, the MCP/watcher probe
`evaluation/phase1b/mcp_watcher.py` with `mcp_server_guard.py` verified this
against the real `bm mcp` stdio server with an active watcher
(run `20261115T102626.362434Z`), extending the earlier CLI-level probe
(`20261115T091717.382049Z`). A deployment keeps the property as a host
characteristic by not providing sqlite-vec; `HF_HUB_OFFLINE=1` blocks downloads
but not the use of cached models while sqlite-vec loads. This is the supported
configuration verification that the 1B phase calls for; see [[Embedding
exception]].

- relates_to [[Embedding exception]]