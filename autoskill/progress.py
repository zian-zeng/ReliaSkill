from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_progress_state(
    output_dir: str | Path | None,
    *,
    phase: str,
    status: str,
    task_id: str | None = None,
    tool_name: str | None = None,
    condition: str | None = None,
    model_name: str | None = None,
    model_slug: str | None = None,
    shard_index: int | None = None,
    num_shards: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a small heartbeat for external progress monitors.

    The heartbeat is intentionally outside result files, so monitoring does not
    affect benchmark scoring, resume behavior, or metric aggregation.
    """
    if output_dir is None:
        return
    root = Path(output_dir).parent
    progress_dir = root / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "phase": phase,
        "status": status,
        "task_id": task_id,
        "tool_name": tool_name,
        "condition": condition,
        "model_name": model_name,
        "model_slug": model_slug,
        "shard_index": shard_index,
        "num_shards": num_shards,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    target = progress_dir / f"{phase}_state.json"
    tmp = target.with_name(f"{target.stem}.{os.getpid()}.{time.time_ns()}.tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(5):
            try:
                tmp.replace(target)
                return
            except PermissionError:
                time.sleep(0.02 * (attempt + 1))
        try:
            target.write_text(text, encoding="utf-8")
        except OSError:
            pass
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
