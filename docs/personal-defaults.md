# Reusable personal defaults

The owner approved both concrete note drafts in chat on 17 November 2026. They
are saved in the productive native `personal` project and verified through native
reads, combined active text recall and comparison with the approved drafts.

## Adopted notes and provenance

| Native identifier in `personal` | Content | Source |
| --- | --- | --- |
| `preferences/working-preferences.md` | Concise communication, minimal scoped changes, comments, installation/configuration approval, Git safety, SSH remotes and test preferences | Owner-provided general AGENTS instructions from the 17 November 2026 conversation; matching toolbox shared instructions |
| `preferences/python-guidelines.md` | Visible errors, `pathlib`, isolated deterministic unit tests, external boundaries, dependency injection and behavior assertions | [Python coding guidelines](python-coding-guidelines.md), introduced in repository commit `d7951c2`, reviewed at `da1c7f7` |

The approved contents remain available as local review drafts under
`.state/personal-defaults/drafts/`. They contain `kind: durable`, `status: active`
and source references. The toolbox instruction source has SHA-256
`de12e837223750c39e4ee9d1f06cef6bbb7e4501f6ca6997aac9ab7a9b8bd85a`;
the reviewed Python source has SHA-256
`0a165b611143f4c6ab915aac6a4541dca3f2d6e203e81e07cd9bd0f883ef10a7`.

The owner explicitly approved adopting the Python draft as shared personal
defaults. Repository-specific integration-test names, marker implementation,
`uv` commands and required Ruff/Pyrefly/pytest checks remain in the project
documentation. The adoption does not turn those tools or conventions into global
requirements or remove existing project guidance.

The authoritative reusable notes live outside repositories in
`$HOME/SharedMemory/notes/personal/preferences/`. This document records identifiers,
provenance and verification rather than duplicating the defaults in each checkout.
Current instructions, project rules and actual code retain precedence under
[ADR 0010](adr/0010-source-aware-memory-and-current-project-authority.md).

## Productive storage verification

Both notes were created with native `bm_write`, explicit `project="personal"`
and `overwrite=false` after approval. Native `bm_read` returned both complete
notes with `kind: durable`, `status: active` and their sources. A native text
search for `"defaults"`, scoped to
`projects=["personal", "harness-independent-shared-memory"]` with
`filters={"status": "active"}`, returned exactly these two notes from `personal`.
The current project's active recall was empty before adoption; no project
handover or additional durable note was introduced for this check.

The external files were compared with the approved drafts: body text and all
approved metadata match. Basic Memory added native `type` and `permalink` fields,
serialized tags as YAML lists and removed the final newline. Productive file
SHA-256 checksums are:

| Note | SHA-256 |
| --- | --- |
| `preferences/working-preferences.md` | `a520657de783f76830f298d1a669d228df7569bd1783540b8f0f62b7d9440019` |
| `preferences/python-guidelines.md` | `8daebfa866a054578bc67260943d406cbbf20dc9fd77ea13b448bfb2d66f60df` |

## Targeted recall verification

The local probe `.state/personal-defaults/verify.py` reuses the existing
[real-client runners](../evaluation/clients/behavior.py), the installed shared
instructions and normal coding tools. Only native server routing is overridden;
the productive store and client configurations are unchanged. Copies of the
proposals are fixtures, not an adoption into productive durable memory.

Both actual checkouts, this repository and `$HOME/toolbox`, use a single
disposable model-free native store. It contains the two personal notes once,
one temporary project-context note for each checkout, and an active unrelated
handover in a third fixture project. Project-context notes have independent
random tokens. The ordinary first question asks about Python work, installation
preferences and the current project's continuation context, without instructing
the client to search memory.

The checks cover explicit combined `personal`/current-project text searches with
active status, reads of the personal Python guidelines and current project's note,
the correct random token, exclusion of other projects' tokens and no memory writes
by clients. Raw transcripts are retained
under `.state/personal-defaults/*-verify/`.

A synthetic conflicting personal test-name default checks that this repository's
actual integration-test convention wins. The toolbox follow-up checks its actual
requirement for a script purpose comment against the general preference for
comments that explain non-obvious reasons. These are fixture-only checks; the
conflicting default and test handovers will not be saved into productive memory.
Precedence answers require inspection alongside the automated retrieval checks.

The initial run is
`.state/personal-defaults/20261117T175318.519711Z-verify/`. Codex passed scoped
recall, exact-token reproduction and project-rule precedence in this repository.
In the toolbox turn it read the correct personal and project notes, but its final
answer substituted a different 32-character token for the actual project token.
The exact-token assertion rejected that answer; correct retrieval alone was not
counted as a passing continuation check. The original transcript and unchanged
fixture remain available in `codex-toolbox/`. The repeat in `codex-toolbox-repeat/`
reproduced the exact token. It sourced installation approval from the already
loaded global AGENTS instructions rather than rereading the identical proposed
working-preferences note; current instructions are valid authoritative evidence.

OpenCode passed in this repository. Its first toolbox invocation inherited this
repository's `PWD` despite `subprocess` receiving `cwd=$HOME/toolbox`; the session
used this repository's context and read its handover. That trace in
`opencode-toolbox/` is rejected as a toolbox check. Setting `PWD` to the actual
checkout produced the correct toolbox scope, token and purpose-comment rule in
`opencode-toolbox-pwd/`. The [existing runner](../evaluation/clients/behavior.py)
now aligns both values. No global configuration change was needed.

`verified-matrix.json` records separate checks of the four successful retained
client/repository traces: combined active text scopes, personal Python and current
project reads, exact own token, no foreign tokens and no memory writes. The
precedence answers in both repositories were also inspected. This is targeted
fixture evidence with retained failures, not a claim that model answers always
copy retrieved facts correctly. Productive adoption was verified separately above.

## Proposed session learning

Pending separate approvals, add this convention to this project's AGENTS.md and
save it as a durable note in the `harness-independent-shared-memory` memory
project: **When launching OpenCode for another checkout, set `PWD` and subprocess
`cwd` to the same absolute directory so configuration, instructions and project
recall use the intended checkout.** Sources: the paired `opencode-toolbox/` and
`opencode-toolbox-pwd/` traces above and the runner change. Scoped active memory
search found no existing PWD note. Neither destination has been updated.

## Repository checks

The changed runner passes Ruff lint, formatting and Pyrefly. Repository-wide
Ruff lint passes. The full format check reports five unchanged historical files;
Pyrefly reports 11 errors in unchanged code. The isolated suite has 85 passing
tests and 22 passing subtests; five tests fail on the already recorded mismatch
between source content and corpus/source pin (three historical OpenCode checks
and two preparation checks). The source, its pin and the corpus were left intact.
The integration suite passed all 19 tests and nine subtests with the necessary
local process/socket permissions; the sandboxed attempt was interrupted after
socket restrictions caused a failure. The four client/repository recall checks
are separate from these regression suites.
No software was installed or updated; commands used the installed locked
environment with `UV_NO_SYNC=1` and `UV_OFFLINE=1`.
