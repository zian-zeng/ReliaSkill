import json
import tempfile
import unittest
from pathlib import Path

from scripts.make_tables import PAPER_TABLES, build_cost_latency_rows, write_all_tables


class PaperTableGenerationTests(unittest.TestCase):
    def test_cost_latency_rows_include_generation_and_behavior_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            audit_path = run / "audit_records.jsonl"
            records = [
                {
                    "run_id": "run_1",
                    "event_type": "skill_generation",
                    "condition": "naive_skill",
                    "model_name": {"generator": "heuristic", "predictor": "heuristic"},
                    "quantization": {"generator": "none", "predictor": "none"},
                    "raw_prompt": "generate compact skill",
                    "raw_model_output": "generated json skill",
                },
                {
                    "run_id": "run_1",
                    "event_type": "behavior_prediction",
                    "condition": "naive_skill",
                    "model_name": "heuristic",
                    "quantization": "none",
                    "raw_prompt": "select arguments for request",
                    "raw_model_output": "{\"arguments\": {}}",
                    "behavior_report": {"result": {"prediction_latency_ms": 12.5}},
                },
            ]
            audit_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

            rows = [row for row in build_cost_latency_rows(run) if row["run_id"] == "run_1"]

            self.assertEqual({row["event_type"] for row in rows}, {"skill_generation", "behavior_prediction"})
            generation = next(row for row in rows if row["event_type"] == "skill_generation")
            behavior = next(row for row in rows if row["event_type"] == "behavior_prediction")
            self.assertGreater(generation["total_tokens_est"], 0)
            self.assertEqual(behavior["avg_latency_ms"], 12.5)

    def test_write_all_tables_exports_csv_and_latex_for_every_paper_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tables"
            tables = {name: [{column: "1" for column in meta["columns"]}] for name, meta in PAPER_TABLES.items()}
            paths = write_all_tables(tables, out)

            self.assertEqual(set(paths), set(PAPER_TABLES))
            for name in PAPER_TABLES:
                self.assertTrue((out / f"{name}.csv").exists())
                tex_path = out / f"{name}.tex"
                self.assertTrue(tex_path.exists())
                text = tex_path.read_text(encoding="utf-8")
                self.assertIn("Auto-generated from ReliaSkill logs", text)
                self.assertIn("\\begin{table}", text)


if __name__ == "__main__":
    unittest.main()
