from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.live_exec.task_builder import build_live_exec_tasks, write_live_task_stats, write_live_tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic live/sandbox execution tasks.")
    parser.add_argument("--output", type=Path, default=Path("data/live_exec/live_tasks.jsonl"))
    parser.add_argument("--stats", type=Path, default=Path("outputs/tables/live_exec_task_stats.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = build_live_exec_tasks()
    write_live_tasks(args.output, tasks)
    write_live_task_stats(args.stats, tasks)
    print(f"tasks={len(tasks)}")
    print(f"output={args.output}")
    print(f"stats={args.stats}")


if __name__ == "__main__":
    main()
