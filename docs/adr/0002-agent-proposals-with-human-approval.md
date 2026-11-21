# Capture knowledge through agent proposals and human approval

> **Superseded by [ADR 0013](0013-technical-approval-for-durable-writes.md).** Chat approval is still how a proposal is presented, but durable writes are now technically gated; this document is retained as the historical decision.

Personal memory must support capturing new findings during work, not only recalling a curated corpus. The agent prepares and proactively presents the proposed memory entry so the human only needs to approve it; incorporation into durable memory requires explicit human approval. This keeps capture convenient while leaving the decision about what becomes durable knowledge with the owner.

Approval is given in the conversation, after which the agent saves the presented entry using its write access. A separate approval service or technically enforced reviewer boundary is outside the required scope. This is a workflow convention rather than a security boundary: personal use does not eliminate prompt-injection risk from retrieved content, and this approach accepts that residual risk in exchange for simplicity.
