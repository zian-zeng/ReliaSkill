from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.experiment import load_tools, run_packaging_pipeline


RAW_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
OUT_ROOT = Path("outputs")


def main() -> None:
    tools = load_tools(RAW_PATH)
    _, summary, _ = run_packaging_pipeline(tools=tools, output_dir=OUT_ROOT)
    for tool_name in tools:
        condition_text = ", ".join(
            f"{baseline} valid={summary[baseline]['valid_rate'] > 0}"
            for baseline in ("raw_mcp", "schema_only", "retrieved_docs", "retrieved_candidates", "retrieved_memory", "generated_skill_base")
            if baseline in summary
        )
        print(f"{tool_name}: {condition_text}")


if __name__ == "__main__":
    main()
