from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.converters.bfcl_converter import convert_bfcl
from reliaskill.converters.common import infer_schema_from_signature, normalize_schema


class ExternalConverterTests(unittest.TestCase):
    def test_schema_normalization_preserves_nested_objects_and_enums(self) -> None:
        schema = normalize_schema(
            {
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["fast", "safe"]},
                        "options": {"type": "object", "properties": {"dry_run": {"type": "boolean"}}},
                    },
                    "required": ["mode", "missing"],
                }
            }
        )

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["mode"])
        self.assertIn("options", schema["properties"])
        self.assertEqual(schema["properties"]["mode"]["enum"], ["fast", "safe"])

    def test_signature_parser_does_not_turn_literals_into_arguments(self) -> None:
        fixed_model = infer_schema_from_signature("AutoModel.from_pretrained('org/model-name')")
        keyword_call = infer_schema_from_signature("client.search(query='cats', limit=5)")

        self.assertEqual(fixed_model["properties"], {})
        self.assertIn("query", keyword_call["properties"])
        self.assertIn("limit", keyword_call["properties"])

    def test_bfcl_converter_outputs_traceable_toolir_and_gold_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "bfcl" / "data"
            (root / "api").mkdir(parents=True)
            (root / "apibench").mkdir(parents=True)
            api_record = {
                "domain": "Search",
                "framework": "Example",
                "functionality": "Search",
                "api_name": "ExampleSearch",
                "api_call": "client.search(query='x', limit=5)",
                "api_arguments": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                "description": "Search an example index.",
            }
            (root / "api" / "example_api.jsonl").write_text(json.dumps(api_record) + "\n", encoding="utf-8")
            example_record = {
                "code": "###Instruction: Find documents about reliability.\n###Output: <<<api_call>>>: client.search(query='reliability', limit=5)",
                "api_call": "client.search(query='x', limit=5)",
                "provider": "Example",
                "api_data": api_record,
            }
            (root / "apibench" / "example_eval.json").write_text(json.dumps([example_record]), encoding="utf-8")

            records, skipped, warnings = convert_bfcl(Path(tmpdir))

        self.assertFalse(warnings)
        self.assertEqual(sum(skipped.values()), 0)
        self.assertGreaterEqual(len(records), 2)
        example = next(record for record in records if record.get("positive_control"))
        for key in [
            "tool_id",
            "source_type",
            "source_name",
            "original_benchmark_id",
            "original_tool_name",
            "original_function_signature",
            "normalized_schema",
            "natural_language_request",
            "gold_tool_call",
            "split_suggestion",
        ]:
            self.assertIn(key, example)
        self.assertEqual(example["source_type"], "bfcl")
        self.assertIn("tool_name", example["toolir"])
        self.assertEqual(example["positive_control"]["should_trigger"], True)

    def test_cli_warns_on_missing_source_without_strict_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            out_dir = tmpdir_path / "converted"
            stats_out = tmpdir_path / "external_conversion_stats.csv"
            report_out = tmpdir_path / "external_conversion_report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/convert_external_benchmarks.py",
                    "--input",
                    str(tmpdir_path),
                    "--output",
                    str(out_dir),
                    "--sources",
                    "api_bank",
                    "--stats-out",
                    str(stats_out),
                    "--report-out",
                    str(report_out),
                ],
                check=True,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertIn("warning=api_bank: missing API-Bank directory", result.stdout)
            self.assertTrue((out_dir / "conversion_records.jsonl").exists())
            self.assertTrue(stats_out.exists())
            self.assertTrue(report_out.exists())


if __name__ == "__main__":
    unittest.main()
