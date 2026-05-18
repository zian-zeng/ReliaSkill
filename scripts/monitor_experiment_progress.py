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
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
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
        expand=True,
    )
    task_ids = {
        "total": progress.add_task("Entire experiment", total=max(plan.total, 1)),
        "benchmark": progress.add_task("Structured-call benchmark", total=max(plan.benchmark_total, 1)),
        "routing": progress.add_task("Hidden-tool routing", total=max(plan.routing_total, 1)),
    }
    if plan.live_total:
        task_ids["live"] = progress.add_task("Live execution", total=plan.live_total)
    started_at = time.monotonic()
    samples: list[tuple[float, int]] = []

    def render_once() -> Group:
        now = time.monotonic()
        snapshot = scan_progress(plan)
        stats = _observed_stats(samples, now=now, completed=int(snapshot["completed"]), total=int(snapshot["total"]))
        progress.update(task_ids["total"], total=max(snapshot["total"], 1), completed=snapshot["completed"])
        progress.update(task_ids["benchmark"], total=max(snapshot["benchmark"]["total"], 1), completed=snapshot["benchmark"]["completed"])
        progress.update(task_ids["routing"], total=max(snapshot["routing"]["total"], 1), completed=snapshot["routing"]["completed"])
        if "live" in task_ids:
            progress.update(task_ids["live"], total=max(snapshot["live"]["total"], 1), completed=snapshot["live"]["completed"])
        return Group(
            _summary_panel(Panel, box, snapshot, elapsed_seconds=now - started_at, stats=stats),
            progress,
            _current_panel(Panel, box, snapshot),
        )

    if args.once:
        from rich.console import Console

        Console().print(render_once())
        return

    with Live(render_once(), refresh_per_second=1, screen=False) as live:
        while True:
            live.update(render_once())
            time.sleep(max(1.0, args.refresh))


def _summary_panel(panel_cls, box_module, snapshot: dict, *, elapsed_seconds: float, stats: dict) -> object:
    total = snapshot["total"] or 0
    completed = snapshot["completed"] or 0
    percent = (completed / total * 100.0) if total else 0.0
    rate_text = f"{stats['rate_per_min']:.1f} records/min" if stats.get("rate_per_min") else "warming up"
    text = (
        f"[bold]Output[/bold] {snapshot['output_root']}\n"
        f"[bold]Completed[/bold] {completed}/{total} ({percent:.1f}%)\n"
        f"[bold]Elapsed[/bold] {_format_duration(elapsed_seconds)}\n"
        f"[bold]Observed ETA[/bold] {stats['eta_text']}  [dim]({rate_text}, from saved result files)[/dim]"
    )
    return panel_cls(text, title="ReliaSkill Experiment Progress", box=box_module.ASCII)


def _current_panel(panel_cls, box_module, snapshot: dict) -> object:
    rows = _active_rows(snapshot.get("current") or [])
    if not rows:
        return panel_cls("No active shard heartbeat yet. The counters above are authoritative.", title="Active Shards", box=box_module.ASCII)
    lines = []
    for row in rows:
        shard = row.get("shard_index") if row.get("shard_index") is not None else "-"
        task = str(row.get("task_id") or "-")
        tool = str(row.get("tool_name") or "-")
        condition = str(row.get("condition") or "-")
        lines.append(
            f"shard {shard} | {row.get('phase') or '-'} | {row.get('status') or '-'} | {condition}\n"
            f"  task: {task}\n"
            f"  tool: {tool}"
        )
    return panel_cls("\n\n".join(lines), title="Active / Next Shard Work", box=box_module.ASCII)


def _active_rows(rows: list[dict]) -> list[dict]:
    rank = {"running": 0, "next": 1, "done": 2}
    phase_rank = {"benchmark": 0, "routing": 1, "live": 2, "done": 3}
    best: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("model_slug") or row.get("model_name") or "-"), str(row.get("shard_index")))
        existing = best.get(key)
        if existing is None or (
            rank.get(str(row.get("status")), 9),
            phase_rank.get(str(row.get("phase")), 9),
        ) < (
            rank.get(str(existing.get("status")), 9),
            phase_rank.get(str(existing.get("phase")), 9),
        ):
            best[key] = row
    return [
        row for row in sorted(best.values(), key=lambda item: (str(item.get("model_slug") or ""), str(item.get("shard_index"))))
        if row.get("status") != "done"
    ]


def _observed_stats(samples: list[tuple[float, int]], *, now: float, completed: int, total: int) -> dict:
    samples.append((now, completed))
    cutoff = now - 1800.0
    del samples[: max(0, next((index for index, (ts, _) in enumerate(samples) if ts >= cutoff), len(samples) - 1))]
    previous = next(((ts, count) for ts, count in samples if count < completed), None)
    if previous is None:
        return {"eta_text": "waiting for result-file delta", "rate_per_min": 0.0}
    prev_ts, prev_completed = previous
    elapsed = max(0.001, now - prev_ts)
    rate_per_second = (completed - prev_completed) / elapsed
    if rate_per_second <= 0:
        return {"eta_text": "waiting for result-file delta", "rate_per_min": 0.0}
    remaining = max(0, total - completed)
    return {"eta_text": _format_duration(remaining / rate_per_second), "rate_per_min": rate_per_second * 60.0}


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


def _short(value: object, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


if __name__ == "__main__":
    main()
