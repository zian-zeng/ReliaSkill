from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.experiment import load_tools, run_benchmark_pipeline


RAW_PATH = Path("data/raw/sample_tools.json")
TASK_PATH = Path("data/eval/sample_tasks.json")
OUT_ROOT = Path("outputs/task_eval")


def main() -> None:
    tools = load_tools(RAW_PATH)
    _, summary, _ = run_benchmark_pipeline(tools=tools, tasks_path=TASK_PATH, output_dir=OUT_ROOT)
    for baseline_name, row in summary.items():
        print(
            f"{baseline_name}: "
            f"exact_match={row['exact_match_rate']:.4f}, "
            f"arg_validity={row['avg_argument_validity']:.4f}"
        )


if __name__ == "__main__":
    main()
