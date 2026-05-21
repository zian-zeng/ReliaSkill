#!/usr/bin/env python3
"""Rank currently available Slurm GPU nodes by GPU strength.

Run on a Nexus/CML login node:

  python3 scripts/cluster/rank_available_gpus.py --min-gpus 4
  python3 scripts/cluster/rank_available_gpus.py --min-gpus 8 --partitions scavenger,cml-scavenger

The script is intentionally read-only: it only calls sinfo, scontrol, and
optionally sacctmgr to print user associations.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, Iterable, List


GPU_STRENGTH = {
    "h200-sxm": 1000,
    "h200": 995,
    "h100-sxm": 960,
    "h100-nvl": 950,
    "h100": 940,
    "a100": 900,
    "l40s": 850,
    "rtx6000ada": 835,
    "rtx6000-ada": 835,
    "rtxa6000": 800,
    "a6000": 800,
    "rtxa5000": 720,
    "a5000": 720,
    "rtxa4000": 610,
    "a4000": 610,
    "rtx4090": 600,
    "rtx3090": 560,
    "rtx3070": 430,
    "rtx2080ti": 400,
    "gtx1080ti": 280,
    "titanxp": 260,
    "titanxpascal": 250,
    "gtxtitanx": 220,
    "p6000": 210,
    "p100": 180,
    "gpu": 1,
}


@dataclass
class Candidate:
    node: str
    partition: str
    state: str
    gpu_type: str
    free: int
    total: int
    alloc: int
    mem_gb: int
    free_mem_gb: int
    cpus: int
    time_limit: str
    planned: bool

    @property
    def strength(self) -> int:
        return gpu_strength(self.gpu_type)

    @property
    def score(self) -> int:
        penalty = 50_000 if self.planned else 0
        return self.strength * 100_000 + self.free * 1_000 + self.free_mem_gb - penalty


def run_text(args: List[str]) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)


def try_text(args: List[str]) -> str:
    try:
        return run_text(args)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def parse_key_values(text: str) -> Dict[str, str]:
    return {match.group(1): match.group(2) for match in re.finditer(r"(\w+)=([^ \n]+)", text)}


def parse_gres(gres: str) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    if not gres or gres == "(null)":
        return totals
    for item in gres.split(","):
        item = item.strip()
        match = re.match(r"gpu(?::([^:,()]+))?(?::(\d+))?", item)
        if not match:
            continue
        gpu_type = normalize_gpu_type(match.group(1) or "gpu")
        count = int(match.group(2) or "1")
        totals[gpu_type] = totals.get(gpu_type, 0) + count
    return totals


def parse_tres_gpus(tres: str) -> tuple[Dict[str, int], int]:
    typed: Dict[str, int] = {}
    generic = 0
    if not tres:
        return typed, generic
    for item in tres.split(","):
        if item.startswith("gres/gpu:"):
            left, _, right = item.partition("=")
            gpu_type = normalize_gpu_type(left.split(":", 1)[1])
            try:
                typed[gpu_type] = int(right)
            except ValueError:
                pass
        elif item.startswith("gres/gpu="):
            try:
                generic = int(item.split("=", 1)[1])
            except ValueError:
                generic = 0
    return typed, generic


def normalize_gpu_type(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace("nvidia-", "")


def gpu_strength(gpu_type: str) -> int:
    normalized = normalize_gpu_type(gpu_type)
    if normalized in GPU_STRENGTH:
        return GPU_STRENGTH[normalized]
    compact = normalized.replace("-", "")
    if compact in GPU_STRENGTH:
        return GPU_STRENGTH[compact]
    for key, score in GPU_STRENGTH.items():
        if key in normalized or key in compact:
            return score
    return 1


def parse_int(value: str | None, default: int = 0) -> int:
    if not value:
        return default
    match = re.match(r"(\d+)", value)
    return int(match.group(1)) if match else default


def node_candidates(node: str, partition: str, state: str, time_limit: str) -> List[Candidate]:
    detail = try_text(["scontrol", "show", "node", node])
    kv = parse_key_values(detail)
    gres = kv.get("Gres", "")
    cfg_tres = kv.get("CfgTRES", "")
    alloc_tres = kv.get("AllocTRES", "")
    state = kv.get("State", state)
    totals = parse_gres(gres)
    alloc_typed, alloc_generic = parse_tres_gpus(alloc_tres)
    _, cfg_generic = parse_tres_gpus(cfg_tres)
    if not totals and cfg_generic:
        totals = {"gpu": cfg_generic}
    mem_gb = round(parse_int(kv.get("RealMemory")) / 1024)
    free_mem_gb = round(parse_int(kv.get("FreeMem")) / 1024)
    cpus = parse_int(kv.get("CPUTot") or kv.get("CPUs"))
    rows: List[Candidate] = []
    for gpu_type, total in totals.items():
        if gpu_type in alloc_typed:
            alloc = alloc_typed[gpu_type]
        elif len(totals) == 1:
            alloc = alloc_generic
        else:
            alloc = 0
        rows.append(
            Candidate(
                node=node,
                partition=partition.rstrip("*"),
                state=state,
                gpu_type=gpu_type,
                free=max(total - alloc, 0),
                total=total,
                alloc=alloc,
                mem_gb=mem_gb,
                free_mem_gb=free_mem_gb,
                cpus=cpus,
                time_limit=time_limit,
                planned="PLANNED" in state,
            )
        )
    return rows


def state_is_usable(state: str, *, include_planned: bool, include_drain: bool) -> bool:
    bad = ("DOWN", "FAIL", "MAINT", "NO_RESP", "POWER")
    if any(token in state for token in bad):
        return False
    if not include_drain and "DRAIN" in state:
        return False
    if not include_planned and "PLANNED" in state:
        return False
    return True


def collect_candidates(args: argparse.Namespace) -> List[Candidate]:
    partitions = {item.strip() for item in (args.partitions or "").split(",") if item.strip()}
    fmt = "%N|%P|%T|%80G|%m|%c|%l"
    rows = run_text(["sinfo", "-N", "-h", "-o", fmt]).splitlines()
    seen: set[tuple[str, str, str]] = set()
    candidates: List[Candidate] = []
    for row in rows:
        fields = row.split("|")
        if len(fields) < 7:
            continue
        node, partition, state, _gres, _mem, _cpus, time_limit = [field.strip() for field in fields[:7]]
        partition = partition.rstrip("*")
        if partitions and partition not in partitions:
            continue
        for candidate in node_candidates(node, partition, state, time_limit):
            key = (candidate.node, candidate.partition, candidate.gpu_type)
            if key in seen:
                continue
            seen.add(key)
            if candidate.free < args.min_gpus:
                continue
            if not state_is_usable(candidate.state, include_planned=args.include_planned, include_drain=args.include_drain):
                continue
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def print_associations() -> None:
    if not shutil.which("sacctmgr"):
        return
    text = try_text(["sacctmgr", "-n", "-P", "show", "assoc", f"user={current_user()}", "format=Account,Partition,QOS%50"])
    if not text.strip():
        return
    print("== Your Slurm associations ==")
    print("account|partition|qos")
    print(text.strip())
    print()


def current_user() -> str:
    return try_text(["id", "-un"]).strip() or "unknown"


def print_table(candidates: Iterable[Candidate], top: int, request_gpus: int | None) -> None:
    rows = list(candidates)[:top]
    if not rows:
        print("No matching free GPU candidates found.")
        print("Try --min-gpus 1, --include-planned, or omit --partitions.")
        return
    header = (
        f"{'#':>2} {'score':>7} {'node':<12} {'partition':<16} {'state':<18} "
        f"{'gpu':<14} {'free/total':>10} {'free_mem':>8} {'mem':>7} {'cpu':>5} {'time':>10}"
    )
    print(header)
    print("-" * len(header))
    for index, row in enumerate(rows, start=1):
        print(
            f"{index:>2} {row.strength:>7} {row.node:<12} {row.partition:<16} {row.state:<18} "
            f"{row.gpu_type:<14} {row.free:>4}/{row.total:<5} {row.free_mem_gb:>6}G {row.mem_gb:>5}G {row.cpus:>5} {row.time_limit:>10}"
        )
    best = rows[0]
    gpus = min(request_gpus or best.free, best.free)
    print()
    print("== Best immediate request template ==")
    print(
        f"salloc -p {best.partition} --gres=gpu:{best.gpu_type}:{gpus} "
        "--cpus-per-task=32 --mem=120G --time=12:00:00"
    )
    print("# Add -A/--account and --qos if this partition requires them.")
    print("# For example: -A cml-scavenger --qos=cml-scavenger on cml-scavenger/scavenger.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-gpus", type=int, default=1, help="Minimum free GPUs of the same type on one node.")
    parser.add_argument("--request-gpus", type=int, default=None, help="GPU count to put in the request template.")
    parser.add_argument("--top", type=int, default=30, help="Number of ranked rows to print.")
    parser.add_argument(
        "--partitions",
        default="",
        help="Comma-separated partition filter, e.g. cml-dpart,cml-scavenger,scavenger,class,gamma.",
    )
    parser.add_argument("--include-planned", action="store_true", help="Include nodes marked PLANNED.")
    parser.add_argument("--include-drain", action="store_true", help="Include nodes marked DRAIN/DRAINING.")
    parser.add_argument("--no-assoc", action="store_true", help="Do not print sacctmgr associations.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not shutil.which("sinfo") or not shutil.which("scontrol"):
        raise SystemExit("Run this on a Slurm login node with sinfo and scontrol available.")
    if args.min_gpus < 1:
        raise SystemExit("--min-gpus must be >= 1")
    if not args.no_assoc:
        print_associations()
    candidates = collect_candidates(args)
    print_table(candidates, top=args.top, request_gpus=args.request_gpus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
