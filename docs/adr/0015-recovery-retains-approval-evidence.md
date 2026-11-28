# Retain approval evidence and close open proposals on recovery

A store snapshot must include the approval gate's proposal files and audit log so
a restore retains the evidence of durable writes. Configure `proposals_dir` as
`<store-root>/approvals` and `audit_log` as `<store-root>/approval-audit.jsonl`.
`memory-ops backup` uses these paths, coordinates with the gate's locks, and
includes the approval files in the manifest.

Recovery never replays a proposal. Restore closes every `pending` proposal as
`closed_by_recovery` and leaves `applying` and `outcome_unknown` unchanged. The
approval CLI accepts only `pending`, so neither a closed nor an uncertain
proposal can be approved after recovery. If a write is still wanted, the agent
submits a new proposal; after an uncertain outcome, the owner checks the restored
store before resubmitting. Terminal proposals and the audit log remain as
history.

The gate configuration is outside the snapshot. After activation it must point
at the restored paths, like the native configuration described in the
[backup procedure](../productive-backup.md#approval-state). This supplements the
approval policy in [ADR 0013](0013-technical-approval-for-durable-writes.md).
