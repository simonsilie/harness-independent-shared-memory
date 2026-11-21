# Native coverage of personal memory behavior

Checked on 17 November 2026 against installed Basic Memory 1.0.0 with disposable
local projects. This completes the roadmap's coverage assessment, not productive
setup. No packages, global client configuration or existing memory were changed.
The model-free configuration gap was later closed by the
[approved local installation](model-free-operation.md#approved-local-installation);
this check alone used the simulated missing-dependency fallback.

## Reproduction and evidence

```sh
uv run --locked --no-sync python evaluation/native/native_memory_coverage.py
```

The probe starts an unconstrained native MCP server behind the existing
inference/network guard. It creates seven fixture notes in `personal`, `alpha`
and `beta`, uses native tools for search and conditional updates, then invokes
`okf export` once per project. Raw calls, tool schemas, export files, configuration
and guards are retained in `evaluation/phase1b/runs/*-native-coverage/`.
Only a run reaching `result.json` counts as passing.

Passing evidence: `evaluation/phase1b/runs/20261117T155003.220030Z-native-coverage/`.
The server and three export processes recorded zero inference import attempts
and zero outbound connections, with only the intentional `sqlite_vec` rejection.
No model files were downloaded; historical corpus and exported source files
remained byte-identical. This check used the simulated missing-dependency
fallback, not the patched productive configuration.

## Requirement mapping

| Requirement | Concrete native operation and result | Remaining work |
| --- | --- | --- |
| Shared personal defaults plus current-project knowledge (ADRs 0004, 0010) | `bm_search(query=..., projects=["personal", "alpha"], mode="text")` returned both projects and no `beta` handover. Results identify their project. `bm_read(project=..., identifier=...)` reads the selected note. | Client instructions must supply both scopes, read useful hits, and apply current-project rules first. A default project does not automatically include personal defaults. No adapter is needed for combined scope. |
| Ordinary project boundary and explicit cross-project lookup (0004) | `project="alpha"` excluded `beta`; explicit `project="beta"` retrieved its handover. `all_projects=true` returned all seven notes. | Use explicit scopes during ordinary recall; reserve all-project lookup for explicit requests. The server must allow multiple projects: launching with `mcp --project alpha` constrains it, so that configuration cannot serve shared personal recall. This is relevance policy, not a protected authorization boundary. |
| Temporary versus durable content (0003) | Frontmatter `kind: temporary` or `kind: durable` survives write, read, filtering and export. `bm_search(filters={"kind":"temporary", ...})` selects temporary notes. | These fields are fixture conventions, not reserved native lifecycle controls. Adopt one consistent convention in client instructions. Durable writes still require chat approval; the tool itself does not enforce approval. |
| Completion and seven inactive days (0003) | Unfiltered search returned `completed`, `archived` and an authored old `last_activity` note. Filtering `status="active"` still returned the old note. Adding `last_activity: {"$gte":"2026-11-10T00:00:00Z"}` selected only the recent temporary handover. | No automatic lifecycle rule was found. A caller must update activity, calculate the cutoff/extension, exclude completed/expired entries immediately and mark them archived. A time filter alone does not persist archival state. |
| Explicit archive search, retention and restore (0003, 0008) | `filters={"status":"archived"}` retrieved the archived note. `bm_read` followed by `bm_write(expected_checksum=...)` restored its status and activity; filtered active search then found it. A second conditional write rearchived it. All fixture notes remained present. | Conditional content mutation suffices for logical archive/restore; physical moves are unnecessary. Ordinary recall must always exclude archive content. No automatic deletion should be introduced. Existing [native client checks](native-client-writes.md) establish stale-update conflicts; this probe does not repeat that race. |
| Readable complete content export (0009) | `basic-memory okf export DEST --project NAME --json` succeeded for all three projects. Bundles preserved each fixture body, `kind`, `status`, activity and source fields, including active, inactive, completed and archived handovers. Each root index names its project; note permalinks retain project prefixes. | Export every configured project into distinct named bundle directories. A single project's export is not the complete store. The format is Markdown/YAML with an OKF 0.2 index and `bm.okf_export` extension. Inspect the actual productive store separately; no recovery or alternate-engine import is established here. |

Ordinary recall can use separate native queries for durable content and active
temporary context, across the personal/current-project scopes. The temporary
query needs both status and activity conditions. Search every page needed for
the operation; the small fixture fits on one page. Read the selected notes to
recover lifecycle/provenance metadata rather than relying on the search excerpt.

## Gaps, reproduction and smallest remedies

**Automatic lifecycle is a behavior gap, not missing storage primitives.**
`single-project.json` reproduces archived/completed inclusion;
`active-filter-still-includes-inactive.json` reproduces the insufficiency of
status alone. `temporary-with-cutoff.json`, `archive-explicit.json` and
`restore-visible.json` demonstrate the available primitives. Source inspection
of installed `config.py`, `mcp/tools/` and `services/` found no completion,
seven-day inactivity, extension or automatic activity-refresh policy.

The smallest initial remedy is a shared client convention: save activity in UTC,
refresh it on every temporary update, allow an explicit extension, conditionally
archive completed/expired entries at recall or update, and apply exclusion
filters before returning ordinary recall. An outage must not silently turn an
expired entry into active context. If real-client verification cannot make this
reliable, add only a lifecycle operation wrapping native conditional writes and
filtered reads. No background daemon or complete workflow deployment is justified
by this probe. Automatic transitions and extensions still require implementation
and verification in the later lifecycle roadmap task.

**Default scope, approval and precedence are missing client instructions.**
Explicit multi-project search works; it does not cause startup recall, enforce
approval, or resolve contradictory guidance. Configure this once in each client
and verify ordinary sessions in the existing client-setup task. Do not duplicate
personal preferences into every repository or use an all-project search as the
ordinary default.

**Whole-store export needs orchestration, not a replacement exporter.**
Native export accepts one project per invocation. Enumerate the configured local
projects and preserve their names as bundle directory names. This can initially
be a documented command sequence. No adapter is justified for the demonstrated
fixture content. The later portable-export task must inspect all actual
productive content and document the chosen format independently of backup.

## Limits and implementation consequence

The dates and cutoff are fixed test data. The old activity value was authored in
a newly created note; no seven-day wall-clock expiry or background archival was
observed. Retention means no fixture was removed during this check, not a
long-duration guarantee. There was no client model turn, startup instruction
verification, owner-preference import, productive export, backup restore or
software selection in this task. Attachments, arbitrary link conversion and
alternate-engine imports were not exercised.

Native scope, metadata, conditional writes and per-project export cover the
required data primitives. Keep the existing workflow as retained evidence while
resolving the global model-free gap and verifying the small client lifecycle
convention. These findings do not justify deploying the full workflow, changing
installed dependencies or claiming productive readiness.
