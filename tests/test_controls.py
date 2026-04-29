from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from autoskill.control_generation import build_controls, load_control_config, load_toolir_records, summarize_controls


REQUIRED_CONTROL_FIELDS = {
    "category",
    "gold_tool",
    "gold_args",
    "should_trigger",
    "rationale",
    "split",
}


class ControlGenerationTests(unittest.TestCase):
    def test_minimum_config_generates_strong_positive_and_negative_coverage(self) -> None:
        config = load_control_config("configs/controls/minimum.yaml")
        controls = build_controls(config)
        summary = summarize_controls(controls)

        self.assertEqual(summary["tools"], len(load_toolir_records(config["tools_path"])))
        self.assertGreaterEqual(summary["min_positive_per_tool"], 5)
        self.assertGreaterEqual(summary["min_negative_per_tool"], 7)
        self.assertEqual(summary["dev_controls"], summary["test_controls"])

        categories = set(summary["categories"])
        self.assertIn("positive", categories)
        for category in config["negative_categories"]:
            self.assertIn(category, categories)

    def test_control_records_are_backward_compatible_and_have_gold_labels(self) -> None:
        config = load_control_config("configs/controls/minimum.yaml")
        controls = build_controls(config)
        ids = set()
        per_tool = defaultdict(lambda: Counter({"positive": 0, "negative": 0}))
        requests_by_tool_split = defaultdict(set)

        for control in controls:
            self.assertTrue(REQUIRED_CONTROL_FIELDS.issubset(control))
            self.assertIn(control["split"], {"dev", "test"})
            self.assertIsInstance(control["gold_args"], dict)
            self.assertIsInstance(control["rationale"], str)
            self.assertNotIn(control["id"], ids)
            ids.add(control["id"])

            bucket = "positive" if control["should_trigger"] else "negative"
            per_tool[control["tool_key"]][bucket] += 1
            requests_by_tool_split[(control["tool_key"], control["split"])].add(control["user_request"])

            if control["should_trigger"]:
                self.assertEqual(control["gold_tool"], control["tool_name"])
                self.assertEqual(control["expected_arguments"], control["gold_args"])
            else:
                self.assertEqual(control["negative_target"], control["tool_name"])
                self.assertIn("negative", control["tags"])

        self.assertTrue(per_tool)
        self.assertTrue(all(counts["positive"] >= 5 for counts in per_tool.values()))
        self.assertTrue(all(counts["negative"] >= 7 for counts in per_tool.values()))

    def test_build_controls_cli_writes_dev_test_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source_tools = Path("data/processed_toolir/tools.jsonl").read_text(encoding="utf-8").splitlines()[:4]
            tools_path = tmpdir_path / "tools.jsonl"
            tools_path.write_text("\n".join(source_tools) + "\n", encoding="utf-8")
            config_path = tmpdir_path / "controls.yaml"
            config = {
                "seed": 42,
                "tools_path": str(tools_path),
                "positive_controls_per_tool": 5,
                "outputs": {
                    "dev": str(tmpdir_path / "controls" / "dev.jsonl"),
                    "test": str(tmpdir_path / "controls" / "test.jsonl"),
                    "stats": str(tmpdir_path / "tables" / "control_stats.csv"),
                },
            }
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

            subprocess.run(
                [sys.executable, "scripts/build_controls.py", "--config", str(config_path)],
                check=True,
                cwd=Path.cwd(),
            )

            dev_path = Path(config["outputs"]["dev"])
            test_path = Path(config["outputs"]["test"])
            stats_path = Path(config["outputs"]["stats"])
            self.assertTrue(dev_path.exists())
            self.assertTrue(test_path.exists())
            self.assertTrue(stats_path.exists())

            dev_records = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines()]
            test_records = [json.loads(line) for line in test_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(dev_records), len(test_records))
            self.assertEqual(len(dev_records) + len(test_records), 4 * 12)

            with stats_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertTrue(rows)
            self.assertIn("category", rows[0])
            self.assertIn("control_count", rows[0])

    def test_tiered_controls_have_difficulty_and_failure_mode_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source_tools = Path("data/processed_toolir/tools.jsonl").read_text(encoding="utf-8").splitlines()[:4]
            tools_path = tmpdir_path / "tools.jsonl"
            tools_path.write_text("\n".join(source_tools) + "\n", encoding="utf-8")
            config = load_control_config("configs/controls/emnlp_scale.yaml")
            config["tools_path"] = str(tools_path)
            config["outputs"] = {
                "dev": str(tmpdir_path / "controls" / "dev.jsonl"),
                "test": str(tmpdir_path / "controls" / "test.jsonl"),
                "stats": str(tmpdir_path / "tables" / "control_stats.csv"),
                "difficulty_stats": str(tmpdir_path / "tables" / "control_difficulty_stats.csv"),
                "negative_category_stats": str(tmpdir_path / "tables" / "negative_category_stats.csv"),
            }
            controls = build_controls(config)
            summary = summarize_controls(controls)

            self.assertEqual(summary["tools"], 4)
            self.assertEqual(summary["min_positive_per_tool"], 5)
            self.assertEqual(summary["min_negative_per_tool"], 5)
            self.assertEqual(set(summary["difficulties"]), {"easy", "medium", "hard"})
            self.assertEqual(set(summary["families"]), {"positive", "negative"})

            categories = set(summary["categories"])
            for category in [
                "positive_easy",
                "positive_medium",
                "positive_hard",
                "negative_easy",
                "negative_medium",
                "negative_hard",
            ]:
                self.assertIn(category, categories)

            required_new_fields = {
                "control_id",
                "difficulty",
                "control_family",
                "negative_category",
                "expected_failure_mode",
                "alternative_valid_tools",
            }
            for control in controls:
                self.assertTrue(required_new_fields.issubset(control))
                self.assertIn(control["difficulty"], {"easy", "medium", "hard"})
                self.assertIn(control["control_family"], {"positive", "negative"})
                self.assertIsInstance(control["alternative_valid_tools"], list)
                if control["control_family"] == "positive":
                    self.assertTrue(control["should_trigger"])
                    self.assertIsNone(control["negative_category"])
                else:
                    self.assertFalse(control["should_trigger"])
                    self.assertIsInstance(control["negative_category"], str)
                    self.assertTrue(control["expected_failure_mode"])

            dev_requests = {control["user_request"] for control in controls if control["split"] == "dev"}
            test_requests = {control["user_request"] for control in controls if control["split"] == "test"}
            self.assertFalse(dev_requests & test_requests)

            from autoskill.control_generation import write_controls_outputs

            outputs = write_controls_outputs(config, controls)
            self.assertTrue(Path(outputs["difficulty_stats"]).exists())
            self.assertTrue(Path(outputs["negative_category_stats"]).exists())

            with Path(outputs["difficulty_stats"]).open("r", encoding="utf-8") as f:
                difficulty_rows = list(csv.DictReader(f))
            self.assertTrue(difficulty_rows)
            self.assertIn("difficulty", difficulty_rows[0])

            with Path(outputs["negative_category_stats"]).open("r", encoding="utf-8") as f:
                negative_rows = list(csv.DictReader(f))
            negative_categories = {row["negative_category"] for row in negative_rows}
            self.assertIn("similar_tool_should_be_used", negative_categories)
            self.assertIn("ambiguous_abstain_safer", negative_categories)


if __name__ == "__main__":
    unittest.main()
