# Record lightweight handover observations automatically

Agents automatically record standardized observations of handover use during real work, while owner corrections and feedback remain optional. Use a local structured log outside repositories, separate from the memory knowledge entries; start with a shared template and existing tools, adding a small writer only if reliable recording exposes a demonstrated tooling gap. A dashboard and full conversation copies are outside this requirement.

Retrieving a handover is not proof of successful continuation. Record failures and required reminders as well as successes, use `unknown` or `unrated` when evidence is missing, and reference the continuing session rather than copying its transcript. The agent's assessment and optional owner feedback remain distinguishable.

Use JSON Lines, with one observation per line. The following expanded example illustrates one observation; the data directory is selected during setup.

```json
{
  "timestamp": "2026-11-17T12:00:00Z",
  "project": "example-project",
  "handover_id": "example-handover",
  "from_client": "opencode",
  "to_client": "codex",
  "found_without_reminder": "yes",
  "continuation": "partial",
  "problem_or_assistance": "Owner supplied a missing pending check.",
  "session_reference": "example-continuing-session",
  "owner_feedback": null
}
```

`found_without_reminder` is `yes`, `no`, or `unknown`; `continuation` is the agent's evidence-based assessment of `successful`, `partial`, `failed`, or `unrated`. Unknown identifiers and other unavailable details are `null`, never invented. Recording this metadata does not promote handover content into durable knowledge or enable live capture by itself.
