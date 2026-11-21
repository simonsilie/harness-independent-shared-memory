# Reusable personal defaults

Store owner-approved preferences in the `personal` project as active durable
notes. Record sources and use the current project's instructions and code to
resolve conflicting defaults. See [ADR 0010](adr/0010-source-aware-memory-and-current-project-authority.md).
The [Python coding guidelines](python-coding-guidelines.md) illustrate a
public source that can support a reusable default.

Verify that ordinary text recall combines personal defaults with the current
project's knowledge. Use a disposable store with synthetic preferences, a
current-project handover and an unrelated project. Check that each client reads
the relevant notes, excludes unrelated entries and follows project rules when
they conflict with a default.

The disposable verification confirmed scoped recall and project-rule
precedence. It also showed that checking the answer matters independently of
checking which notes the client read. When launching OpenCode in a selected
checkout, the [runner](../evaluation/clients/behavior.py) aligns `PWD` with
the subprocess working directory. Keep approved personal notes, their
identifiers and raw verification evidence local.
