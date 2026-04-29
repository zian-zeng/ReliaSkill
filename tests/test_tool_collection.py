from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoskill.tool_collection import collect_tool_records, load_collection_config, stable_schema_hash, summarize_dataset


class ToolCollectionTests(unittest.TestCase):
    def test_minimum_config_collects_paper_scale_tool_set(self) -> None:
        config = load_collection_config("configs/data/minimum.yaml")
        records = collect_tool_records(config)
        summary = summarize_dataset(records)

        self.assertGreaterEqual(summary["total_tools"], 80)
        self.assertGreaterEqual(summary["source_count"], 8)
        self.assertGreaterEqual(summary["domain_count"], 8)
        self.assertEqual(summary["synthetic_tools"], 0)

        first = records[0]
        self.assertIn("source_metadata", first)
        for key in [
            "server",
            "domain",
            "side_effect_type",
            "auth_required",
            "args_count",
            "required_args_count",
            "enum_count",
        ]:
            self.assertIn(key, first["source_metadata"])

    def test_dedup_key_keeps_schema_variants(self) -> None:
        config = {
            "seed": 42,
            "sources": [
                {
                    "id": "fixture",
                    "type": "mcp_fixture",
                    "path": "data/raw/sample_tools.json",
                    "limit": 3,
                }
            ],
        }
        records = collect_tool_records(config)
        seen = set()
        for record in records:
            metadata = record["source_metadata"]
            key = (metadata["source_server"], record["name"], stable_schema_hash(record["inputSchema"]))
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_collection_cli_writes_raw_toolir_stats_and_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_path = tmpdir_path / "minimum.yaml"
            config = load_collection_config("configs/data/minimum.yaml")
            config["outputs"] = {
                "raw_tools": str(tmpdir_path / "raw" / "tools.jsonl"),
                "toolir": str(tmpdir_path / "toolir" / "tools.jsonl"),
                "dataset_stats": str(tmpdir_path / "tables" / "dataset_stats.csv"),
                "dataset_card": str(tmpdir_path / "reports" / "dataset_card.md"),
            }
            config["max_tools"] = 100
            config_path.write_text(json.dumps(config), encoding="utf-8")

            subprocess.run(
                [sys.executable, "scripts/collect_mcp_tools.py", "--config", str(config_path)],
                check=True,
                cwd=Path.cwd(),
            )

            raw_path = Path(config["outputs"]["raw_tools"])
            toolir_path = Path(config["outputs"]["toolir"])
            stats_path = Path(config["outputs"]["dataset_stats"])
            card_path = Path(config["outputs"]["dataset_card"])
            self.assertTrue(raw_path.exists())
            self.assertTrue(toolir_path.exists())
            self.assertTrue(stats_path.exists())
            self.assertTrue(card_path.exists())

            raw_records = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
            toolir_records = [json.loads(line) for line in toolir_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(raw_records), len(toolir_records))
            self.assertGreaterEqual(len(raw_records), 80)

            with stats_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertTrue(rows)
            self.assertIn("source_id", rows[0])


if __name__ == "__main__":
    unittest.main()
