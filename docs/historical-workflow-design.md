# Historical workflow service design (Option A)

Historical design only: the former contract is superseded by the ADRs and
[scope reconciliation](scope-reconciliation.md). The implementation, probes,
tests and commands below belong to tag `historical-workflow-20261118`,
commit [`fe09180fac127bcaf48c87fc29b3577c49300e61`](https://github.com/simonsilie/harness-independent-shared-memory/blob/fe09180fac127bcaf48c87fc29b3577c49300e61/docs/phase-1b-workflow-design.md).
They are not active packages or productive setup instructions; see
[the retirement decision](custom-code-decision.md).

Contract sketch and data model for the approved Option A: an own workflow service
on Basic Memory owns proposals, durable revisions, handovers, retry state and the
protected reviewer boundary. Direction approved by the owner on 15 November 2026;
this document is a design for review, not an implementation release. All
[section 13](../evaluation/harness-independent-shared-memory.md#13-acceptance-criteria-and-rollout-gates)
The former gates apply unchanged. Baselines: [capability inventory](historical-capability-inventory.md),
[native probes E4](evaluation-results.md#native-prerequisite-probes--15-november-2026),
[MCP/watcher probe E5](evaluation-results.md#mcpwatcher-probe--15-november-2026),
[Hindsight screening](historical-alternative-screening.md).

## Ownership and storage layout

| Concern | Owner | Storage |
| --- | --- | --- |
| Accepted knowledge (current content) | Workflow service writes; Basic Memory serves recall | Native Markdown notes + `note_content` in the shared SQLite store |
| Durable revision history, proposals, decisions, handovers, retry state, project registry | Workflow service exclusively | Own `wf_*` tables in the same SQLite database; never exposed as native notes |
| Native primitives | Reused, not reimplemented | Checksum CAS writes, `NoteContentMutationService.on_accepted_mutation()` transaction hook, FTS/text search, read-cache invalidation, SQLite backup |

Rationale: proposals and handovers must never enter the note store, because
native default recall returns any indexed note [E4] and cannot be filtered
reliably from outside. Keeping them in `wf_*` tables makes "accepted-only default
recall" structural instead of filter-based. Storing them in the same database
keeps acceptance atomic with the note mutation — the hook commits and rolls back
additional rows with the note in one transaction [E4] — and keeps one
backup/restore story [E4]. Basic Memory code never reads or writes `wf_*` tables.

A host without sqlite-vec stays the model-independence configuration [E5]; the
workflow service runs in the same process configuration and must not require
inference.

## Data model

All tables prefixed `wf_`, created and migrated by the workflow service only.
Timestamps UTC; JSON columns for structured values. Field names follow
[section 5](../evaluation/harness-independent-shared-memory.md#5-portable-record-contract).

```text
wf_project     project_uuid PK; repository_remote; approved_checkouts json;
               created_at
               -- explicit project UUID mapped to approved repo identities;
               -- the directory path is never the sole identifier

wf_record      record_id PK; project_id FK; scope; owner_id; kind; title;
               tags json; created_by; created_at; current_revision;
               environment json (branch/commit/tool versions, optional)

wf_revision    record_id FK; revision; PK(record_id, revision);
               schema_version; title; body; tags json; sources json;
               status accepted|superseded|expired;
               created_by; created_at; accepted_by; accepted_at;
               verified_at; expires_at; supersedes json; derived_from json;
               native_checksum  -- note checksum after this revision was written
               content_hash     -- independent integrity hash of the body
               -- rows are immutable; supersession is a status change of rows,
               -- never a body edit

wf_proposal    proposal_id PK; target_id; base_revision nullable;
               target_exists bool;           -- reserved new id vs. edit
               candidate json;               -- complete content + metadata:
                                             -- kind/title/body/tags/sources/
                                             -- verified_at/expires_at
               proposed_by; proposed_at; status proposed|accepted|rejected;
               idempotency_key
               -- immutable after insert; corrections require a new proposal

wf_decision    decision_id PK; proposal_id FK; decision accepted|rejected;
               reviewer; decided_at; reason; resulting_revision nullable;
               base_checksum_checked   -- what acceptance actually compared

wf_handover    handover_id PK; project_id FK; owner_id; kind 'handover';
               status active|completed|expired; title; summary; body;
               branch; base_commit; environment json;
               revision;                      -- bumped per update, CAS target
               expires_at NOT NULL; created_by; created_at; updated_at;
               completed_at; completed_by
               -- handovers are never native notes and never unreviewed-free:
               -- they are always labelled unreviewed work

wf_operation   caller; operation; idempotency_key; PK(caller, operation,
               idempotency_key); payload_hash; result json; created_at
               -- retry ledger; same key + changed payload hash = rejection
```

The link to native state: `wf_revision.native_checksum` records the note
checksum as of that revision's acceptance. A proposal with `base_revision`
points at a revision row; acceptance compares the note's live checksum against
that row's `native_checksum`, never against a freshly fetched one.

## Agent facade (MCP tools for the three clients)

The early read-only `bm_search`/`bm_read` allowlist is replaced by the
workflow facade; this is a recorded client-configuration change, re-verified per
client like [E1](evaluation-results.md). The facade exposes exactly:

| Tool | Behaviour |
| --- | --- |
| `memory.search(query, view=knowledge\|handovers, ...)` | `knowledge` (default): native text search, then facade-level exclusion of superseded/expired revisions, `expires_at` past, and environment-inapplicable records; bounded snippets with source, revision, freshness. `handovers`: active, unexpired handovers of the resolved project, labelled unreviewed, with checkout mismatch display (branch/commit vs. resolved checkout). |
| `memory.get(id, view)` | Record/revision or proposal by ID with status and provenance; explicit views may retrieve pending/rejected and completed/expired objects. |
| `memory.propose(target\|new, candidate, base_revision, idempotency_key)` | Writes one immutable `wf_proposal` row; never touches the note store. Returns `proposal_id`. |
| `memory.save_handover(..., idempotency_key)` / `memory.complete_handover(id, expected_revision, idempotency_key)` | Creates/updates/completes `wf_handover` rows. Updates require `expected_revision`; kind/owner/scope/project are immutable after creation. |

The facade resolves the project via its checkout context (approved checkout list
in `wf_project`), applies scope authorization before counting or snippet
building, and serves its own cache only after re-validating `expires_at` and
status at read time.

Knowledge search follows native pages in rank order and deduplicates record
identities until it fills the requested limit or exhausts results. It scans at
most 1,000 native hits; `incomplete: true` signals a short response when scanning
stops with more native results available.

## Reviewer operations (separate execution identity)

A reviewer CLI/service (`wf`) performs acceptance, rejection, publication,
supersession, deletion, export and handover administration. It runs under a
separate OS identity from the agents; agents hold neither reviewer credentials
nor filesystem access to canonical files. Personal controlled-capture deployment shape:

- One service process owns the storage directory and the database; it serves the
  MCP facade (streamable-http) with per-client agent tokens scoped to
  propose/search/get/handover operations, and the reviewer API with a reviewer
  token. A local stdio server running as the agent's OS user is explicitly not
  used as the boundary.
- Canonical Markdown and `memory.db` are owned and writable only by the service
  identity; agent shell access cannot modify them.

### Acceptance algorithm (the core invariant)

```text
accept(proposal_id, idempotency_key):
  retry ledger lookup → return original result on retry
  load proposal; require status = proposed
  if target_exists:
      expected = wf_revision[base_revision].native_checksum
      write note through NoteContentMutationService with
        expected_checksum = expected        # CAS against the proposal's
                                            # original base, never a fresh read
      on_accepted_mutation:                 # same transaction
        insert wf_revision (full body, status=accepted, supersedes previous,
          native_checksum = post-write checksum)
        insert wf_decision (accepted, reviewer, base_checksum_checked)
        update wf_proposal.status = accepted (+ resulting_revision)
        update wf_revision[previous].status = superseded
        insert wf_operation (payload hash and resulting revision)
  else:
      require the reserved target path absent (ALREADY_EXISTS otherwise)
      create note + revision 1 in the same pattern
  commit → materialize and index; return resulting revision
  transaction failure → full rollback: note, journal, revision, decision, proposal, retry receipt
  follow-up failure → report committed result; same-key retry resumes follow-up
  base mismatch → proposal stays pending, conflict returned, nothing changed
```

Two proposals based on the same revision coexist; accepting the second after the
first fails with `REVISION_CONFLICT` [E4 mechanism]. Rejection writes a
`wf_decision` row and leaves the note store untouched.

## Lifecycle and retries

- Proposals: `proposed → accepted|rejected`, immutable content, no expiry.
- Revisions: `accepted → superseded` on acceptance of a successor; `expired`
  when past `expires_at` (read-time check, history preserved).
- Handovers: `active → completed|expired` independently of review; completion
  and expiry exclude them from the active view; handovers never appear in
  knowledge recall because they are not notes.
- Retries: all three operations (propose, save_handover, accept) are idempotent
  via `wf_operation` scoped to caller + operation; reuse with a different payload
  is rejected; acceptance retries return the original resulting revision.
- Stale handover updates fail on `expected_revision` mismatch.

## Export, import, backup

`uv run --locked python -m workflow.bundle export DATABASE DESTINATION.zip` writes a version 3
logical bundle instead of a database snapshot: canonical native state as JSON
under `native/<project external id>/` (the project row, notes with canonical
`markdown_content` and materialization state, and observations and relations
referenced by external id) and every `wf_*` table verbatim under `workflow/`.
Both come from one deferred read transaction, so an accepted mutation during
export is either wholly in the bundle or wholly absent. Numeric native identities
are not exported and are reassigned at import. The manifest pins bundle version
3, Basic Memory 1.0.0, the workflow table set, and a SHA-256 checksum per entry.

`uv run --locked python -m workflow.bundle import BUNDLE.zip FRESH_CONFIG_DIRECTORY` initializes
a fresh staging database with the native migrations, restores native rows and
workflow rows verbatim in one transaction (no workflow transition is replayed;
idempotent retries resume against the restored receipts), materializes the
canonical note files, validates references and checksum relationships, rebuilds
and verifies the native keyword index, then activates the directory by rename.
It preserves all workflow rows and retry receipts, relocates native project
paths, and writes `config.json`. Start new clients with
`BASIC_MEMORY_CONFIG_DIR` pointing to that directory after import; the
destination must not exist. Original corpus and database access is unnecessary.
Version 3 is schema-independent across Basic Memory 1.0.0 schema layouts;
cross-version schema migration remains outstanding. Older bundle versions are
rejected: version 1 lacks deletion tombstones, and version 2 was the SQLite
snapshot format. Checkout approvals remain the exported project identities.
The native change log and semantic vector projections are not exported, so an
OKF export after restore has no change history and semantic search has no
embeddings until a native re-index; note sections and temporal assertions stay
empty until the next native index pass.

Native hook wiring and schema queries live in `workflow/integration.py`;
workflow transitions remain in `service.py`. The hook still patches Basic
Memory process-wide because Basic Memory has no supported instance extension
point. Keep the dependency pin and run the acceptance, rollback, conflict,
recovery and portability contracts before upgrades:

```sh
uv run --locked pytest tests/workflow tests/evaluation/workflow/test_workflow_integration.py -k 'not review_boundary'
```

Deletion persists an intent before native deletion, then removes workflow rows
and finalizes the receipt together. `wf_deleted_revision` retains only each
deleted revision’s identity, project and deletion time, without its body.
Provenance continues to reference those identities; bundle validation accepts
references to live revisions or these tombstones and rejects unknown targets.
Tombstones are exported workflow metadata; deleted records remain unavailable
to explicit gets and search. Acceptance checks that intent in its native
transaction, fencing both edits and recreation of the same project/path across
processes. `uv run --locked python -m workflow.reviewer pending-deletions` exposes interrupted
operations; `uv run --locked python -m workflow.reviewer recover-deletions --project main`
resumes them. A process-released POSIX file lock serializes recovery attempts
for each record. Recovery also finishes checksum-guarded file cleanup if the native
delete committed before materialization. A changed file or native checksum keeps
the deletion pending for review. Deletion spans transactions; its persisted
intent, rather than a claim of atomic deletion, defines recovery.

## Proof plan (gate → harness)

| Controlled-capture gate | Proof to build |
| --- | --- |
| Model independence | Facade + service run under the E5 condition (no sqlite-vec, blocked inference imports/sockets); storage, keyword recall, proposals and handovers work without any embedding attempt. |
| Cross-client capture | Propose from each of the three clients via the facade, accept via reviewer access, retrieve the accepted revision in the other two. |
| Pending edits | Open and rejected proposals leave accepted body, checksum and default visibility unchanged (structural: proposals are not notes). |
| Stale approval | Two proposals on one base; accept one; the second conflicts without overwrite; a freshly fetched checksum does not unlock it. |
| Handover | Save in client A, resume in client B without reviewer access; unreviewed label, checkout mismatch display; completed/expired leave the active view and never appear in knowledge recall. |
| Lifecycle and retries | Each excluded state absent from default recall with warmed facade cache and after reindex; stale handover update fails; the three retry operations do not duplicate and reuse-with-changed-payload fails. |
| Review boundary | Denials through MCP (agent token), reviewer CLI as agent, backend HTTP and filesystem; authorized reviewer operations succeed, including publication and deletion. |
| Portability and recovery | Export/import and backup restore round-trips with stable identities, full revision history, proposals, decisions, relationships and handovers; rebuilt indexes expose only eligible records. |

## Non-goals

No new engine or migration, no semantic ranking or automatic capture hooks, no
team-phase scope/role model beyond the single-owner boundary, no change to
section 5 fields or the eight controlled-capture gates. The facade renames nothing that exists
for renaming's sake: native write/edit/move/delete tools stay inaccessible to
agents, and the facade implements policy the native tools do not have.
