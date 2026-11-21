import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.recall import prepare
from evaluation.recall.score import score


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.source = b"Temporary context expires after seven days.\n"
        self.source_revision = "sha256:" + hashlib.sha256(self.source).hexdigest()
        self.answer_key = json.loads(
            (Path(__file__).resolve().parents[3] / "evaluation" / "scoring" / "answer-key.json").read_text()
        )
        self.results = [
            {
                "question_id": item["id"],
                "query": "representative question text",
                "mode": "text",
                "retrieved_ids": [item["expected_id"]] if item["expected_id"] else [],
                "recognized_missing_evidence": item["expected_id"] is None,
            }
            for item in self.answer_key
        ]

    def test_text_mode_scores_and_other_modes_are_rejected(self):
        self.assertTrue(score(self.answer_key, self.results)["retrieval_gate_passed"])
        for mode in (None, "hybrid", "semantic", "vector", "title", ""):
            with self.subTest(mode=mode):
                if mode is None:
                    self.results[0].pop("mode", None)
                else:
                    self.results[0]["mode"] = mode
                with self.assertRaises(ValueError):
                    score(self.answer_key, self.results)

    def test_top_five_and_retrieval_threshold(self):
        answerable = [result for result in self.results if result["retrieved_ids"]]
        for result in answerable[:5]:
            result["retrieved_ids"] = ["irrelevant"] * 5 + result["retrieved_ids"]
        outcome = score(self.answer_key, self.results)
        self.assertEqual(outcome["recall_hits_at_5"], 15)
        self.assertFalse(outcome["retrieval_gate_passed"])

    def test_regeneration_separates_key_and_rejects_changed_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root = Path(temporary)
            source = root / prepare.SOURCE.name
            original = self.source
            source.write_bytes(original)
            with (
                patch.object(prepare, "ROOT", root),
                patch.object(prepare, "SOURCE", source),
                patch.object(prepare, "AUTHORED_SOURCE_REVISION", self.source_revision),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    prepare.main()
                questions = json.loads((root / "questions.json").read_text())
                key = json.loads((root / "scoring/answer-key.json").read_text())
                self.assertEqual(len(questions), 22)
                self.assertTrue(all(set(item) == {"id", "question"} for item in questions))
                self.assertEqual(key, self.answer_key)
                before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and p != source}
                with contextlib.redirect_stdout(io.StringIO()):
                    prepare.main()
                self.assertEqual({p: p.read_bytes() for p in before}, before)
                changed = original.replace(b"expires after seven days", b"expires after three days")
                self.assertNotEqual(changed, original)
                source.write_bytes(changed)
                with self.assertRaises(SystemExit):
                    prepare.main()
                after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and p != source}
                self.assertEqual(after, before)

    def test_corpus_revisions_match_the_pinned_source(self):
        revision = "sha256:" + hashlib.sha256(prepare.SOURCE.read_bytes()).hexdigest()
        self.assertEqual(revision, prepare.AUTHORED_SOURCE_REVISION)
        corpus = Path(__file__).resolve().parents[3] / "evaluation" / "corpus"
        notes = sorted(corpus.glob("memory-*.md"))
        self.assertEqual(len(notes), 20)
        for note in notes:
            with self.subTest(note=note.name):
                self.assertIn(f'source_revision: "{revision}"', note.read_text())

    def test_question_ids_are_independent_of_records_and_no_answers_are_mixed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root = Path(temporary)
            source = root / prepare.SOURCE.name
            source.write_bytes(self.source)
            with (
                patch.object(prepare, "ROOT", root),
                patch.object(prepare, "SOURCE", source),
                patch.object(prepare, "AUTHORED_SOURCE_REVISION", self.source_revision),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                prepare.main()
                questions = json.loads((root / "questions.json").read_text())
                key = json.loads((root / "scoring/answer-key.json").read_text())
                self.assertEqual(len({item["id"] for item in questions}), 22)
                for item in questions:
                    self.assertRegex(item["id"], r"^q-[0-9a-f]{16}$")
                missing_positions = [i for i, item in enumerate(key) if item["expected_id"] is None]
                self.assertEqual(len(missing_positions), 2)
                self.assertTrue(all(0 < i < len(key) - 1 for i in missing_positions))
                record_order = [item["expected_id"] for item in key if item["expected_id"]]
                self.assertNotEqual(record_order, sorted(record_order))
                with patch.object(prepare, "DATA", list(reversed(prepare.DATA))):
                    prepare.main()
                reordered = json.loads((root / "questions.json").read_text())
                self.assertEqual(
                    {item["question"]: item["id"] for item in questions},
                    {item["question"]: item["id"] for item in reordered},
                )


if __name__ == "__main__":
    unittest.main()
