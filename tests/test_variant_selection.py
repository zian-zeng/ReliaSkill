from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autoskill.variant_selection import (
    apply_selection_manifest,
    load_dev_evidence,
    select_method_variant,
    write_selection_manifest,
)


class VariantSelectionTests(unittest.TestCase):
    def test_refuses_test_or_heldout_input_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_path = root / "prediction_records.jsonl"
            self._write_jsonl(
                test_path,
                [
                    {
                        "split": "test",
                        "baseline_name": "generated_skill_base",
                        "task_id": "t1",
                        "joint_exact_match": True,
                    }
                ],
            )
            with self.assertRaisesRegex(ValueError, "Dev-only variant selection refuses"):
                load_dev_evidence(prediction_record_paths=[test_path])

            heldout_path = root / "routing_records.jsonl"
            self._write_jsonl(
                heldout_path,
                [
                    {
                        "split": "heldout",
                        "baseline_name": "generated_skill_base",
                        "task_id": "r1",
                        "joint_exact_match": True,
                    }
                ],
            )
            with self.assertRaisesRegex(ValueError, "Dev-only variant selection refuses"):
                load_dev_evidence(routing_record_paths=[heldout_path])

    def test_harm_penalty_beats_positive_gain(self) -> None:
        records = []
        for index in range(10):
            records.append(self._structured("aggressive", f"pos_a_{index}", should_trigger=True, joint=True))
        for index in range(2):
            records.append(self._structured("aggressive", f"neg_a_{index}", should_trigger=False, selected="demo_tool"))
        for index in range(6):
            records.append(self._structured("cautious", f"pos_c_{index}", should_trigger=True, joint=True))
        for index in range(4):
            records.append(self._structured("cautious", f"miss_c_{index}", should_trigger=True, joint=False))
        for index in range(2):
            records.append(self._structured("cautious", f"neg_c_{index}", should_trigger=False, selected="__abstain__"))

        manifest = select_method_variant(records)

        self.assertEqual(manifest["selected_condition"], "cautious")
        aggressive = self._candidate(manifest, "aggressive")
        cautious = self._candidate(manifest, "cautious")
        self.assertGreater(aggressive["harm_rate"], cautious["harm_rate"])
        self.assertGreater(cautious["dev_selection_score"], aggressive["dev_selection_score"])

    def test_tie_breaks_toward_shorter_artifact(self) -> None:
        records = [
            self._structured("compact_variant", "task_1", should_trigger=True, joint=True, complexity=120),
            self._structured("verbose_variant", "task_1", should_trigger=True, joint=True, complexity=420),
        ]

        manifest = select_method_variant(records)

        self.assertEqual(manifest["selected_condition"], "compact_variant")
        verbose = self._candidate(manifest, "verbose_variant")
        self.assertEqual(verbose["not_selected_reason"], "tie lost to simpler/shorter artifact")

    def test_apply_manifest_copies_selected_existing_package_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "selection_manifest.json"
            manifest = {
                "selection_id": "fixture_selection",
                "selected_condition": "compact_variant",
            }
            write_selection_manifest(manifest, manifest_path)
            source = root / "packages"
            package = source / "demo_tool" / "compact_variant"
            package.mkdir(parents=True)
            (package / "skill.json").write_text('{"baseline_name": "compact_variant"}', encoding="utf-8")

            output = root / "selected_packages"
            applied = apply_selection_manifest(
                manifest_path=manifest_path,
                source_package_root=source,
                output_package_root=output,
                target_condition="selected_variant",
            )

            self.assertEqual(len(applied["copied_packages"]), 1)
            self.assertTrue((output / "demo_tool" / "selected_variant" / "skill.json").exists())
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                apply_selection_manifest(
                    manifest_path=manifest_path,
                    source_package_root=source,
                    output_package_root=output,
                )

    def test_manifest_records_input_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prediction_records.jsonl"
            self._write_jsonl(
                path,
                [self._structured("compact_variant", "task_1", should_trigger=True, joint=True)],
            )
            records, inputs = load_dev_evidence(prediction_record_paths=[path])
            manifest = select_method_variant(records, inputs=inputs)

        self.assertEqual(manifest["selected_condition"], "compact_variant")
        self.assertEqual(len(manifest["inputs"]), 1)
        self.assertRegex(manifest["inputs"][0]["sha256"], r"^[0-9a-f]{64}$")

    @staticmethod
    def _structured(
        condition: str,
        task_id: str,
        *,
        should_trigger: bool,
        joint: bool = False,
        selected: str | None = None,
        complexity: int | None = None,
    ) -> dict:
        record = {
            "split": "dev",
            "record_type": "structured_call",
            "baseline_name": condition,
            "task_id": task_id,
            "tool_name": "demo_tool",
            "expected_tool_name": "demo_tool" if should_trigger else "__abstain__",
            "should_trigger": should_trigger,
            "selected_tool_name": selected if selected is not None else ("demo_tool" if should_trigger else "__abstain__"),
            "triggered": selected != "__abstain__" if selected is not None else should_trigger,
            "joint_exact_match": joint,
            "argument_exact_match": joint,
            "tool_selection_correct": joint if should_trigger else selected == "__abstain__",
        }
        if complexity is not None:
            record["token_overhead_estimate"] = complexity
        return record

    @staticmethod
    def _write_jsonl(path: Path, records: list[dict]) -> None:
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    @staticmethod
    def _candidate(manifest: dict, condition: str) -> dict:
        return next(item for item in manifest["candidates"] if item["condition"] == condition)


if __name__ == "__main__":
    unittest.main()
