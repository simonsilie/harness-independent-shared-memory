# Review of observations from real projects

Working record for the roadmap item [“Review observations from real projects”](ROADMAP.md). Implements [ADR 0011](adr/0011-real-project-use-with-ongoing-evaluation.md) and [ADR 0012](adr/0012-automatic-lightweight-handover-observations.md). The capture format and the automatic-recording rules live in [docs/shared-memory-observations.md](shared-memory-observations.md).

## Agreed first review date

**Saturday 21 November 2026.** Proposed by the owner on 18 November 2026 and confirmed the same day, then moved forward from 25 November 2026 by the owner on 21 November 2026; the review was performed on that date. It is a review date, not a completion gate.

## Working agreement (owner, 18 November 2026)

- Use Codex and OpenCode for upcoming real project work. No artificial tasks and no minimum observation count.
- Let handovers arise at actual work interruptions; the shared rules capture them automatically.
- Correct identifiable misjudgements briefly in chat. Owner feedback stays in the observation's separate `owner_feedback` field.
- At the review, inspect the log and concrete experience for continuations, missed recall, reuse of personal defaults, needed reminders and maintenance burden.
- Little evidence is itself a result and does not automatically close the roadmap item. Only reproducible requirement gaps justify targeted changes.

## Interim review (18 November 2026)

- The productive log `$HOME/SharedMemory/observations/observations.jsonl` holds exactly one real observation: continuation of the `automatic-observations-activation` handover, recorded `2026-11-18T06:12:51Z` with `found_without_reminder=yes` and `continuation=successful`. Source and recording script are in [docs/automatic-observations.md#productive-observations](automatic-observations.md#productive-observations).
- No active temporary handovers at that point. All other `observations.jsonl` files belong to synthetic verification runs with disposable stores and logs.
- No reproducible requirement gap identified from one data point, therefore no focused fix derived. Concurrent-append reliability (384 appends) is already established in [docs/automatic-observations.md](automatic-observations.md).

The open item was recorded as a temporary handover in project `harness-independent-shared-memory` so a session at the review date could resume it and generate a genuine continuation observation; that resumption happened at the 21 November review.

## Review performed (21 November 2026)

Evidence: the productive log `$HOME/SharedMemory/observations/observations.jsonl` (22 observations, 18–21 November 2026), the working agreement above, and the Codex sandbox configuration in `~/.codex/config.toml` and `dotfiles/codex/shared-memory.toml` of the toolbox.

- **Continuations.** Seven handovers produced 10 `successful`, 9 `partial` and 3 `unrated` capture-only records. No records were marked `failed`. The log included repeated successful resumption and a partial continuation across clients.
- **Useful and missed recall.** 18 of 22 records reported unprompted retrieval. Three capture events had an unknown outcome, and one handover was retrieved after a reminder.
- **Reuse of personal defaults.** The active personal notes were recalled during the review. The observation log has no field for measuring their reuse.
- **Reminders.** One reminder-dependent retrieval in 22 records. No standing reminder burden.
- **Maintenance burden.** The 19 November sandbox denial of log appends was reproducible and fixed with a focused change: `sandbox_workspace_write.writable_roots = ["~/SharedMemory/observations"]` in the Codex config and a matching placeholder in the toolbox template. Both parse and the log stays mode 0600. Twelve Codex observations on 20–21 November confirm fresh sessions append without intervention. The log is valid JSONL through 21 November; the review handover was archived on completion, leaving no active temporary handovers in this project.

**Outcome.** The one reproducible requirement gap was fixed and verified in real use; no further reproducible gap justifies a change. The review has been performed, so the roadmap item is complete. This rests on four days of real Codex/OpenCode work rather than an arbitrary observation count; the interim note's little-evidence caution no longer applies.

## Ongoing review

When a personal default or durable project note changes a decision in real work, capture the decision and the note reference in the review record. For a concrete missed recall, capture what was needed and how the session found it. Use these examples alongside the existing handover log.

## Sources

- `ROADMAP.md`, roadmap item “Review observations from real projects”.
- Owner chat decision of 18 November 2026 (review date and working agreement).
- [docs/automatic-observations.md](automatic-observations.md) and [ADRs 0011](adr/0011-real-project-use-with-ongoing-evaluation.md) / [0012](adr/0012-automatic-lightweight-handover-observations.md).
