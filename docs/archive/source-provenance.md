# Corpus provenance and the source revision

The recall corpus is derived from [the architecture proposal](../../evaluation/harness-independent-shared-memory.md), whose
SHA-256 is pinned in [`AUTHORED_SOURCE_REVISION`](../../evaluation/recall/prepare.py).
On 18 November 2026 the working copy and that pin were reconciled deliberately,
without regenerating the corpus. This note records the difference, its reviewed
impact and the limits of the check.

## Difference between the pinned and the current source

| State | Revision | Origin |
| --- | --- | --- |
| Authored / previously pinned | `sha256:109ea610…62aa` | Commit `31906b1`, after corpus acceptance |
| Current working copy | `sha256:49b0153b…53de` | Commit `2b3c892` (scope and roadmap update) |

The only change is one sentence in section 8:

```diff
-Use one repository, one owner, and one writer host.
+Keep the curated corpus in one repository, with one owner and one writer host.
+Exercise global read-only retrieval during real work across at least two
+repositories under section 13's everyday-use gate.
```

`git diff 31906b1 HEAD -- harness-independent-shared-memory.md` shows no other
difference, so sections 1–7 and 9–14 are unchanged since the corpus was accepted.
The change matches the historic correction proposal
[C001](everyday-use-observations.md#c001--memory-18-distinguish-corpus-location-from-work-repositories),
which the earlier preparation run captured without altering the corpus.

## Reviewed impact

| Artefact | Impact | Action |
| --- | --- | --- |
| Section 8 summary in `prepare.py` (`Pilot constraints`) | The old sentence "uses one repository" became incomplete: the corpus stays in one repository, but retrieval is exercised across at least two work repositories. | Summary rewritten to match the new sentence. |
| `evaluation/corpus/memory-18.md` | Same inaccuracy: it repeated the old single-repository limit. | Body updated; all other sentences and the `source_section` remain. |
| `evaluation/corpus/memory-19.md` (embedding exception) | The changed sentence does not touch the embedding text. | Unchanged. |
| `evaluation/questions.json`, `evaluation/scoring/answer-key.json` | Question texts and entry order are unchanged, so derived identities stay stable. | Not regenerated; verified byte-identical against a fresh derivation. |
| `review_status` | Owner-directed source-fidelity correction, not a new content review cycle. | Stays `accepted`. |
| Recorded recall runs | Answers quote the earlier `memory-18` wording. | Raw evidence and its `source_revision` values remain historical; no re-scoring. |

The changed sentence cites section 13's everyday-use gate. That gate describes
the original proposal; current work follows the [roadmap](ROADMAP.md) and
[ADR 0011](../adr/0011-real-project-use-with-ongoing-evaluation.md), as recorded in
the [scope reconciliation](scope-reconciliation.md). The corpus records the
architecture's proposal, not current operating instructions.

## Applied changes

- `AUTHORED_SOURCE_REVISION` and the `source_revision` field of all 20 corpus
  notes now carry `sha256:49b0153b…53de`.
- `prepare.py`'s section 8 summary and `evaluation/corpus/memory-18.md` describe the
  corpus-repository and work-repository distinction.
- No other corpus body, question, answer-key entry or evaluator artefact changed.

## Verification

Run from the repository root:

```sh
uv run --locked python - <<'PY'
import contextlib, hashlib, io, tempfile
from pathlib import Path
from evaluation.recall import prepare

source = Path('evaluation/harness-independent-shared-memory.md')
revision = 'sha256:' + hashlib.sha256(source.read_bytes()).hexdigest()
assert revision == prepare.AUTHORED_SOURCE_REVISION

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    with contextlib.redirect_stdout(io.StringIO()):
        prepare.ROOT = root
        prepare.main()
    assert (root / 'questions.json').read_bytes() == Path('evaluation/questions.json').read_bytes()
    assert (root / 'scoring' / 'answer-key.json').read_bytes() == Path('evaluation/scoring/answer-key.json').read_bytes()
print('pin matches; derived question set unchanged')
PY
```

The check derives draft notes and the question set into a temporary directory
only. It confirms that the pin equals the current document hash and that a fresh
derivation yields the checked-in questions and answer key unchanged.

## Limits

- The review covers the one changed paragraph; it does not re-author the whole
  corpus, and the notes remain owner-reviewed paraphrases rather than verbatim
  quotations.
- Draft notes are not compared with the accepted corpus, because review edits
  the corpus deliberately. Regeneration would overwrite accepted wording and
  stays a separate authoring action.
- Historical results keep their recorded wording, revisions and scores. This
  reconciliation does not claim a new evaluation pass, and no client was rerun.
- The productive store is separate from this corpus; the revision change affects
  only the historical recall experiment.
