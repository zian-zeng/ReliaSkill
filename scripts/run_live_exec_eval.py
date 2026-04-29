from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.live_exec.evaluator import (
    evaluate_live_exec_tasks,
    load_live_tasks,
    load_prediction_calls,
    summarize_live_results,
    write_jsonl,
    write_live_results_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run safe live/sandbox execution evaluation over predicted tool calls.")
    parser.add_argument("--tasks", type=Path, default=Path("data/live_exec/live_tasks.jsonl"))
    parser.add_argument("--predictions", type=Path, default=None, help="JSONL with live_task_id and predicted_tool_call.")
    parser.add_argument("--output", type=Path, default=Path("outputs/tables/live_exec_results.csv"))
    parser.add_argument("--details", type=Path, default=Path("outputs/live_exec/live_exec_results.jsonl"))
    parser.add_argument("--use-gold", action="store_true", help="Smoke mode: execute expected_tool_call instead of model predictions.")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke limit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_live_tasks(args.tasks)
    if args.limit:
        tasks = tasks[: args.limit]
    predictions = load_prediction_calls(args.predictions)
    results = evaluate_live_exec_tasks(tasks, predictions, use_gold=args.use_gold)
    write_live_results_csv(args.output, results)
    write_jsonl(args.details, results)
    summary = summarize_live_results(results)
    print(json.dumps(summary, sort_keys=True))
    print(f"results={args.output}")
    print(f"details={args.details}")


if __name__ == "__main__":
    main()
