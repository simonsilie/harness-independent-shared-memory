# Temporary memory and archive

Apply these rules to native Basic Memory through `bm_project`, `bm_search`,
`bm_read` and `bm_write`. They supplement the shared recall and approval rules.

- Before ordinary recall, obtain the current UTC time. Use only `personal` and
  the matched current project. Enumerate temporary notes with separate text
  searches for `filters={"kind":"temporary","status":"active"}` and
  `filters={"kind":"temporary","status":"completed"}`, without a topic query.
  Collect every result page before changing notes; mutations can shift pages.
  Read their complete metadata before using their contents as working context.
- Temporary notes have `kind: temporary`, `status: active` and UTC ISO 8601
  `last_activity`. Their availability ends at `last_activity + 7 days`, or at
  `extended_until` if that explicit owner-approved UTC deadline is later.
  At the deadline they are expired. An extension never overrides completion.
  A missing or YAML-null `extended_until` means no extension. Missing or invalid
  activity, or a non-null invalid extension, means the entry is excluded
  from ordinary recall; report the problem rather than guessing its age.
- On recall, conditionally archive completed and expired entries: set
  `status: archived`, UTC `archived_at` and `archive_reason: completed` or
  `archive_reason: inactive`. Preserve the body, provenance and `last_activity`.
  Do not expose their contents as current context, even if archival fails.
  Report unavailable maintenance briefly and continue independent work.
- Ordinary recall searches active durable notes separately with
  `filters={"kind":"durable","status":"active"}`. Omit `mode` for topic
  queries to use the hybrid default, and use `mode="text"` for exact terms.
  Only temporary notes that passed the metadata/deadline checks may supply
  temporary context. A plain `status: active` result is insufficient. Never
  widen ordinary project scopes.
- Save unfinished work without individual approval in the current project's
  temporary notes. Record where work stopped, what remains and how to resume.
  Every work update refreshes `last_activity` to current UTC; merely reading does
  not. Extension requests set `extended_until` and refresh activity. Do not invent
  extensions. Complete a handover by archiving it immediately, recording
  `archive_reason: completed`, UTC `completed_at` and `archived_at`, and refreshed
  `last_activity`. Do not create durable knowledge from a handover implicitly.
- Search archived notes only on explicit request, with explicit project scopes,
  text mode and `filters={"kind":"temporary","status":"archived"}`. Retain
  them indefinitely until owner-requested deletion. Logical archival changes
  metadata in place; no physical move or deletion is needed.
- On explicit restore, read the archived entry, set `status: active`, refresh
  UTC `last_activity`, and explicitly set `archived_at`, `archive_reason`,
  `completed_at` and `extended_until` to YAML `null` in the content frontmatter.
  Native `bm_write` merges omitted fields back from the old note; omission does
  not clear them. Do not pass these nulls through the separate `metadata` argument,
  which rejects null values. Read back the saved note and verify the reset.
  Preserve the body and sources. It then has a fresh seven-day inactivity window.
- Before every update, including archive, extension, completion and restore,
  read the native revision and pass its `expected_checksum` to `bm_write`.
  Create new notes with `overwrite=false`. On `REVISION_CONFLICT`, preserve the
  winner, report the conflict, and reread before proposing reconciliation; never
  retry stale content with a newer checksum or an unconditional overwrite.
