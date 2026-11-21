import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "harness-independent-shared-memory.md"
AUTHORED_SOURCE_REVISION = "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
DATA = [
    (
        "Shared memory scope",
        "Shared memory preserves durable facts, decisions, lessons, and temporary handovers. It does not transfer live context or hidden reasoning.",
        "2",
        "Does shared memory transfer the live context window?",
    ),
    (
        "Evaluate before building",
        "Evaluate Basic Memory in a read-only recall experiment before implementing a custom memory engine.",
        "1",
        "Which engine should the first experiment evaluate?",
    ),
    (
        "Canonical storage",
        "Choose one canonical representation. Files and database rows must not be independently writable authorities.",
        "3",
        "Can both Markdown and database rows be writable authorities?",
    ),
    (
        "Knowledge visibility",
        "Personal records are owner-only. Project and team records are for authorized members. Scope labels alone do not enforce access.",
        "4",
        "Does a project tag enforce access control?",
    ),
    (
        "Employer separation",
        "Personal and employer knowledge use separate deployments or credentials and stores. Publication is explicit and reviewed.",
        "4",
        "How should personal and employer knowledge be separated?",
    ),
    (
        "Repository authority",
        "Repository documentation remains authoritative for current build instructions and binding project rules. Surface conflicts and verify repository state.",
        "4",
        "What wins when recalled build instructions conflict with repository documentation?",
    ),
    (
        "Project identity",
        "Use a project UUID mapped to approved repository identities and checkouts. A local directory path alone is insufficient.",
        "5",
        "How should project identity survive renames and worktrees?",
    ),
    (
        "Review and verification",
        "Durable knowledge requires explicit human acceptance. Acceptance is distinct from evidence verification; verified_at stays null until evidence is checked.",
        "5",
        "Does accepting a record mean its evidence was verified?",
    ),
    (
        "Proposal immutability",
        "Proposals are separate from accepted records and immutable after submission. Corrections require a new proposal.",
        "5",
        "Can an agent edit a submitted proposal in place?",
    ),
    (
        "Default recall",
        "Default knowledge search returns accepted, unexpired, applicable entries. Handovers use a separate view and are labeled unreviewed.",
        "6",
        "Which records belong in default knowledge recall?",
    ),
    (
        "Review execution boundary",
        "Agents must not have reviewer credentials, unrestricted backend APIs, or shell write access to canonical storage when enforcement is claimed.",
        "6",
        "Does a local stdio server alone enforce review separation?",
    ),
    (
        "Startup retrieval",
        "Resolve the project and search accepted decisions and lessons at task start. Separately inspect handovers and compare their branch and commit with the checkout.",
        "6",
        "What should an agent retrieve at task start?",
    ),
    (
        "Search budget",
        "Start with full-text search and scope, project, type, and validity filters. The initial combined knowledge and handover snippet budget is roughly 2000 tokens.",
        "7",
        "What is the initial recall snippet budget?",
    ),
    (
        "Stale proposal approval",
        "Acceptance compares the proposal original base_revision against the current durable revision. A mismatch conflicts and leaves the proposal pending.",
        "7",
        "What happens when two proposals based on revision four are accepted in sequence?",
    ),
    (
        "Write retries",
        "Idempotency keys are scoped to authenticated caller and operation. A retry returns the original result; reuse with a different payload fails.",
        "7",
        "How are duplicate write retries handled?",
    ),
    (
        "Handover expiry",
        "Handovers are personal by default, expire after seven days by default, and do not become accepted knowledge by being saved.",
        "4",
        "How long does a handover last by default?",
    ),
    (
        "Read time expiry",
        "Check expires_at at read time, including cached results. Do not rely on a cleanup job or destroy history to implement expiry.",
        "7",
        "Can expiry wait for a cleanup job?",
    ),
    (
        "Pilot constraints",
        "Phase 1A keeps the curated corpus in one repository with one owner and one writer host, and exercises global read-only retrieval during real work across at least two repositories under section 13's everyday-use gate. The owner seeds 20 to 30 reviewed non-sensitive source-linked records. Agent tools are read-only.",
        "8",
        "What are the phase 1A deployment limits?",
    ),
    (
        "Embedding exception",
        "For phase 1A use text query mode, document local background embeddings as an exception, and configure no hosted embedding provider. Text queries alone do not disable indexing inference.",
        "8",
        "Does text query mode prevent background embeddings?",
    ),
    (
        "SQLite backup safety",
        "Keep SQLite on a local filesystem. Sync completed consistent backups or exported documents instead of a live SQLite or WAL database.",
        "8",
        "Can a live SQLite WAL database be synced between laptops?",
    ),
]


def main():
    revision = "sha256:" + hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if revision != AUTHORED_SOURCE_REVISION:
        raise SystemExit(
            "Source changed: review and update DATA against the source before updating AUTHORED_SOURCE_REVISION."
        )
    corpus = ROOT / "draft-corpus"
    corpus.mkdir(exist_ok=True)
    entries: list[tuple[str, str | None]] = []
    for number, (title, body, section, question) in enumerate(DATA, 1):
        record_id = "memory-%02d" % number
        metadata = {
            "title": title,
            "type": "note",
            "permalink": record_id,
            "id": record_id,
            "scope": "project",
            "project_id": "b9e8a625-31be-4bc8-8a1d-cb233ab53394",
            "review_status": "pending-owner-review",
            "source_uri": "../harness-independent-shared-memory.md",
            "source_revision": revision,
            "source_section": section,
        }
        frontmatter = "\n".join("%s: %s" % (key, json.dumps(value)) for key, value in metadata.items())
        (corpus / (record_id + ".md")).write_text("---\n" + frontmatter + "\n---\n\n# " + title + "\n\n" + body + "\n")
        entries.append((question, record_id))
    entries.extend(
        [
            ("Which Jenkins version does our production server run?", None),
            ("What is the employer memory service API credential?", None),
        ]
    )
    random.Random(0).shuffle(entries)
    questions = []
    answer_key = []
    for question, record_id in entries:
        question_id = "q-" + hashlib.sha256(question.encode()).hexdigest()[:16]
        questions.append({"id": question_id, "question": question})
        answer_key.append({"id": question_id, "expected_id": record_id})
    (ROOT / "questions.json").write_text(json.dumps(questions, indent=2) + "\n")
    scoring = ROOT / "scoring"
    scoring.mkdir(exist_ok=True)
    (scoring / "answer-key.json").write_text(json.dumps(answer_key, indent=2) + "\n")
    print("Prepared 20 draft notes and 22 questions; no engine configured.")


if __name__ == "__main__":
    main()
