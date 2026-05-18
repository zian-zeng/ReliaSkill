from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.progress_monitor import build_progress_plan, scan_progress


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Rich live progress dashboard for a ReliaSkill experiment.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--num-shards", type=int, default=None)
    parser.add_argument("--models", default="all", help="Comma-separated model names/slugs/config paths, or 'all'.")
    parser.add_argument("--skip-routing", action="store_true")
    parser.add_argument("--refresh", type=float, default=10.0)
    parser.add_argument("--once", action="store_true", help="Render one dashboard frame and exit.")
    return parser.parse_args()


def main() -> None:
    try:
        from rich import box
        from rich.console import Group
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    except ImportError as exc:
        raise SystemExit("Rich is required for the live progress dashboard. Install with: python -m pip install rich") from exc

    args = parse_args()
    model_filter = [] if args.models == "all" else [item.strip() for item in args.models.split(",") if item.strip()]
    plan = build_progress_plan(
        args.config,
        output_root=args.output_root,
        num_shards=args.num_shards,
        models=model_filter,
        skip_routing=args.skip_routing,
    )
    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("{task.percentage:>5.1f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        expand=True,
    )
    task_ids = {
        "total": progress.add_task("Entire experiment", total=max(plan.total, 1)),
        "benchmark": progress.add_task("Structured-call benchmark", total=max(plan.benchmark_total, 1)),
        "routing": progress.add_task("Hidden-tool routing", total=max(plan.routing_total, 1)),
    }
    if plan.live_total:
        task_ids["live"] = progress.add_task("Live execution", total=plan.live_total)

    def render_once() -> Group:
        snapshot = scan_progress(plan)
        progress.update(task_ids["total"], total=max(snapshot["total"], 1), completed=snapshot["completed"])
        progress.update(task_ids["benchmark"], total=max(snapshot["benchmark"]["total"], 1), completed=snapshot["benchmark"]["completed"])
        progress.update(task_ids["routing"], total=max(snapshot["routing"]["total"], 1), completed=snapshot["routing"]["completed"])
        if "live" in task_ids:
            progress.update(task_ids["live"], total=max(snapshot["live"]["total"], 1), completed=snapshot["live"]["completed"])
        return Group(_summary_panel(Panel, box, snapshot), progress, _current_panel(Panel, box, snapshot))

    if args.once:
        from rich.console import Console

        Console().print(render_once())
        return

    with Live(render_once(), refresh_per_second=1, screen=False) as live:
        while True:
            live.update(render_once())
            time.sleep(max(1.0, args.refresh))


def _summary_panel(panel_cls, box_module, snapshot: dict) -> object:
    total = snapshot["total"] or 0
    completed = snapshot["completed"] or 0
    percent = (completed / total * 100.0) if total else 0.0
    text = (
        f"[bold]Output[/bold] {snapshot['output_root']}\n"
        f"[bold]Completed[/bold] {completed}/{total} ({percent:.1f}%)\n"
        "[dim]ETA is live Rich progress ETA from observed completed result files.[/dim]"
    )
    return panel_cls(text, title="ReliaSkill Experiment Progress", box=box_module.ASCII)


def _current_panel(panel_cls, box_module, snapshot: dict) -> object:
    rows = snapshot.get("current") or []
    if not rows:
        return panel_cls("waiting", title="Current / Next Work By Shard", box=box_module.ASCII)
    lines = []
    for row in rows:
        worker = f"{row.get('model_slug') or row.get('model_name') or '-'} / shard {row.get('shard_index') if row.get('shard_index') is not None else '-'}"
        lines.append(
            " | ".join(
                [
                    _short(worker, 14),
                    _short(row.get("phase") or "-", 9),
                    _short(row.get("status") or "-", 4),
                    _short(row.get("task_id") or "-", 22),
                    _short(row.get("condition") or "-", 8),
                ]
            )
        )
    return panel_cls("\n".join(lines), title="Current / Next Work By Shard", box=box_module.ASCII)


def _short(value: object, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


if __name__ == "__main__":
    main()
