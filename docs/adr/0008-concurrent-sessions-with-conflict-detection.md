# Support concurrent sessions without silent overwrites

Multiple agent sessions may use the same personal memory concurrently and save independent entries in parallel. Updates to the same entry must detect stale state, report a conflict, and preserve the current content instead of silently overwriting a newer change. This requirement applies to both durable knowledge and temporary handovers; it does not require team functionality.
