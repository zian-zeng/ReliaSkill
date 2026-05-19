from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reliaskill.analysis.proof_ledger import (
    audit_runtime_invariants,
    extract_proof_ledger_cases,
    write_invariant_report,
    write_proof_ledger_report,
)


class ProofLedgerTests(unittest.TestCase):
    def test_proof_ledger_extracts_cases_and_passes_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run = Path(tmpdir) / "run"
            _write_jsonl(
                run / "prediction_records.jsonl",
                [
                    _record("accepted", should_call=True, actions=[]),
                    _record("repaired", should_call=True, actions=["filled_grounded_required:query"]),
                    _record("abstained", should_call=False, should_trigger=False, should_call_after=False),
                    _record(
                        "refined-selected",
                        should_call=True,
                        refinement={"attempted": True, "selected_refined": True, "original_score": 0.25, "refined_score": 1.0},
                    ),
                    _record(
                        "refined-rejected",
                        should_call=True,
                        refinement={"attempted": True, "selected_refined": False, "original_score": 1.0, "refined_score": 0.25},
                    ),
                ],
            )

            ledger = extract_proof_ledger_cases(run, max_cases_per_type=1, include_routing=False)
            invariants = audit_runtime_invariants(run, include_routing=False)
            ledger_paths = write_proof_ledger_report(
                ledger,
                output_json=Path(tmpdir) / "reports" / "ledger.json",
                output_md=Path(tmpdir) / "reports" / "ledger.md",
            )
            invariant_paths = write_invariant_report(
                invariants,
                output_json=Path(tmpdir) / "reports" / "invariants.json",
                output_md=Path(tmpdir) / "reports" / "invariants.md",
            )

            self.assertEqual(ledger["case_counts"]["accepted_verified_call"], 1)
            self.assertEqual(ledger["case_counts"]["verifier_repaired_call"], 1)
            self.assertEqual(ledger["case_counts"]["safe_abstention"], 1)
            self.assertEqual(ledger["case_counts"]["refinement_selected"], 1)
            self.assertEqual(ledger["case_counts"]["refinement_rejected"], 1)
            self.assertTrue(invariants["ok"])
            self.assertTrue(Path(ledger_paths["json"]).exists())
            self.assertTrue(Path(invariant_paths["markdown"]).exists())

    def test_invariant_audit_flags_invalid_refinement_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run = Path(tmpdir) / "run"
            _write_jsonl(
                run / "prediction_records.jsonl",
                [
                    _record(
                        "bad-refinement",
                        should_call=True,
                        refinement={"attempted": True, "selected_refined": True, "original_score": 0.5, "refined_score": 0.5},
                    )
                ],
            )

            report = audit_runtime_invariants(run, include_routing=False)

            self.assertFalse(report["ok"])
            self.assertEqual(report["violations"][0]["violation"], "selected_refinement_without_score_gain")


def _record(
    task_id: str,
    *,
    should_call: bool,
    should_trigger: bool = True,
    should_call_after: bool | None = None,
    actions: list[str] | None = None,
    refinement: dict | None = None,
) -> dict:
    predicted_arguments = {"query": "alpha"} if should_call else {}
    metadata = {
        "reliaskill_v1_runtime_verifier": {
            "enabled": True,
            "actions": actions or [],
            "issues": [],
            "should_call_after": should_call if should_call_after is None else should_call_after,
            "verified_arguments": dict(predicted_arguments),
            "original_arguments": dict(predicted_arguments),
            "contract_evaluation_after": {"satisfied": bool(should_call), "proof_obligations": []},
            "contract_evaluation_before": {"satisfied": bool(should_call), "proof_obligations": []},
        }
    }
    if refinement is not None:
        metadata["reliaskill_v1_refinement"] = refinement
    return {
        "baseline_name": "reliaskill_v1",
        "record_type": "benchmark",
        "task_id": task_id,
        "expected_tool_name": "search_docs",
        "selected_tool_name": "search_docs" if should_call else "",
        "should_trigger": should_trigger,
        "should_call": should_call,
        "joint_exact_match": should_call,
        "predicted_arguments": predicted_arguments,
        "prediction_metadata": metadata,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()
