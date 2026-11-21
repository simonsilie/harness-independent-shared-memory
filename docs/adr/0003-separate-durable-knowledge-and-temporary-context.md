# Separate durable knowledge from temporary work context

Personal memory includes both long-term findings and a temporary store for unfinished work and session handovers. Treat temporary context like a computer's temporary directory: it supports continuation without becoming durable knowledge merely because it was saved. This is a logical distinction, not a requirement for separate storage systems.

The agent may save temporary work context without individual human approval. Promotion into durable knowledge requires an explicit human approval in the conversation, preserving control over long-term memory without interrupting routine handovers.

Temporary context captures task state and handovers between agent sessions so work can continue with the relevant context. After seven days without an update, it moves to an archive and is excluded from ordinary recall unless the owner explicitly extends its availability. Completed handovers are archived immediately. Archived entries are retained until the owner explicitly requests permanent deletion; there is no automatic deletion deadline.

A handover records where the session stopped, what remains open, and how to continue. Tasks are handover content; a standalone ticketing or task-management system is outside scope. The archive remains separate from active temporary context, supports explicit search, and allows entries to be restored to active use.
