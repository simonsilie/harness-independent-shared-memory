import json
import sys
from pathlib import Path

import configargparse


def score(questions, results):
    expected = {item["id"]: item["expected_id"] for item in questions}
    if len(results) != len(expected) or {item["question_id"] for item in results} != set(expected):
        raise ValueError("Supply exactly one result per question, including no-answer questions.")
    hits = 0
    no_answers = 0
    for item in results:
        target = expected[item["question_id"]]
        retrieved = item["retrieved_ids"]
        if not isinstance(retrieved, list) or not all(isinstance(value, str) for value in retrieved):
            raise ValueError("retrieved_ids must be a ranked list of stable record IDs.")
        if not isinstance(item.get("query"), str) or not item["query"].strip():
            raise ValueError("Record the actual tool query for each question.")
        if item.get("mode") != "text":
            raise ValueError('Record the actual tool mode; every scored query must use mode="text".')
        if not isinstance(item.get("recognized_missing_evidence"), bool):
            raise ValueError("Record recognized_missing_evidence as a boolean.")
        if target is None:
            no_answers += item["recognized_missing_evidence"]
        else:
            hits += target in retrieved[:5]
    return {
        "recall_hits_at_5": hits,
        "recall_questions": 20,
        "recognized_no_answers": no_answers,
        "no_answer_questions": 2,
        "retrieval_gate_passed": hits >= 16 and no_answers == 2,
    }


def main():
    parser = configargparse.ArgumentParser(description="Score one client recall run, not the full phase 1A gate.")
    parser.add_argument("results", type=Path, nargs="?")
    parser.add_argument(
        "--results", dest="configured_results", type=Path, metavar="PATH", env_var="SHARED_MEMORY_RECALL_RESULTS"
    )
    args = parser.parse_args()
    results_path = args.results or args.configured_results
    if results_path is None:
        parser.error("results is required")
    questions = json.loads((Path(__file__).resolve().parents[1] / "scoring" / "answer-key.json").read_text())
    try:
        result = score(questions, json.loads(results_path.read_text()))
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if result["retrieval_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
