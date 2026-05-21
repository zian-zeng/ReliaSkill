#!/usr/bin/env python3
"""Rank currently available Slurm GPU allocation options.

Run on a Nexus/CML login node:

  python3 scripts/cluster/rank_available_gpus.py --min-gpus 4
  python3 scripts/cluster/rank_available_gpus.py --counts 8,7,6,4,3,2 --partitions scavenger,cml-scavenger
  python3 scripts/cluster/rank_available_gpus.py --request-gpus 8 --min-gpus 4
  python3 scripts/cluster/rank_available_gpus.py --counts 8,7,6,4,3,2 --min-mem-gb 120 --cpus 32

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


GPU_THROUGHPUT = {
    # Rough per-GPU ranking for local HF inference throughput. These are not
    # benchmark claims; they are only meant to compare allocation shapes.
    "h200-sxm": 480,
    "h200": 470,
    "h100-sxm": 430,
    "h100-nvl": 420,
    "h100": 410,
    "a100": 300,
    "l40s": 320,
    "rtx6000ada": 250,
    "rtx6000-ada": 250,
    "rtxa6000": 190,
    "a6000": 190,
    "rtxa5000": 140,
    "a5000": 140,
    "rtx4090": 125,
    "rtx3090": 115,
    "rtxa4000": 95,
    "a4000": 95,
    "rtx3070": 85,
    "rtx2080ti": 70,
    "gtx1080ti": 45,
    "titanxp": 42,
    "titanxpascal": 40,
    "gtxtitanx": 36,
    "p6000": 34,
    "p100": 30,
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
    usable_mem_gb: int
    cpus: int
    free_cpus: int
    time_limit: str
    planned: bool

    @property
    def strength(self) -> int:
        return gpu_strength(self.gpu_type)

    @property
    def score(self) -> int:
        penalty = 50_000 if self.planned else 0
        return self.strength * self.free * 100_000 + self.free_mem_gb - penalty


@dataclass
class AllocationOption:
    candidate: Candidate
    requested: int
    rank_mode: str
    partition_bonus: int = 0
    memory_weight: int = 5000
    memory_score_cap_gb: int = 256

    @property
    def score(self) -> int:
        penalty = 50_000 if self.candidate.planned else 0
        memory_bonus = min(self.candidate.usable_mem_gb, self.memory_score_cap_gb) * self.memory_weight
        if self.rank_mode == "single-gpu":
            return (
                self.candidate.strength * 100_000
                + self.requested * 1_000
                + memory_bonus
                + self.partition_bonus
                - penalty
            )
        return (
            self.candidate.strength * self.requested * 100_000
            + memory_bonus
            + self.partition_bonus
            - penalty
        )


def run_text(args: List[str]) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)


def try_text(args: List[str]) -> str:
    try:
        return run_text(args)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def parse_key_values(text: str) -> Dict[str, str]:
    return {match.group(1): match.group(2) for match in re.finditer(r"(\w+)=([^ \n]+)", text)}


def collect_node_details() -> Dict[str, Dict[str, str]]:
    """Fetch all Slurm node records in one call.

    Calling `scontrol show node <name>` for every node can take minutes on a
    large shared cluster. The one-shot `-o` format keeps each node on one line,
    which is much faster and easier to parse.
    """
    text = try_text(["scontrol", "show", "nodes", "-o"])
    if not text:
        text = try_text(["scontrol", "show", "node", "-o"])
    details: Dict[str, Dict[str, str]] = {}
    for line in text.splitlines():
        kv = parse_key_values(line)
        node = kv.get("NodeName")
        if node:
            details[node] = kv
    return details


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


def parse_tres_int(tres: str, key: str) -> int:
    if not tres:
        return 0
    prefix = f"{key}="
    for item in tres.split(","):
        if item.startswith(prefix):
            return parse_int(item.split("=", 1)[1])
    return 0


def parse_mem_gb(value: str | None) -> int:
    if not value:
        return 0
    match = re.match(r"(\d+(?:\.\d+)?)([KMGTP]?)", value.strip(), re.IGNORECASE)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = match.group(2).upper()
    if unit == "K":
        amount /= 1024 * 1024
    elif unit == "M" or unit == "":
        amount /= 1024
    elif unit == "T":
        amount *= 1024
    elif unit == "P":
        amount *= 1024 * 1024
    return round(amount)


def parse_tres_mem_gb(tres: str) -> int:
    if not tres:
        return 0
    for item in tres.split(","):
        if item.startswith("mem="):
            return parse_mem_gb(item.split("=", 1)[1])
    return 0


def normalize_gpu_type(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace("nvidia-", "")


def gpu_strength(gpu_type: str) -> int:
    normalized = normalize_gpu_type(gpu_type)
    if normalized in GPU_THROUGHPUT:
        return GPU_THROUGHPUT[normalized]
    compact = normalized.replace("-", "")
    if compact in GPU_THROUGHPUT:
        return GPU_THROUGHPUT[compact]
    for key, score in GPU_THROUGHPUT.items():
        if key in normalized or key in compact:
            return score
    return 1


def parse_int(value: str | None, default: int = 0) -> int:
    if not value:
        return default
    match = re.match(r"(\d+)", value)
    return int(match.group(1)) if match else default


def node_candidates(
    node: str,
    partition: str,
    state: str,
    time_limit: str,
    details_by_node: Dict[str, Dict[str, str]],
) -> List[Candidate]:
    kv = details_by_node.get(node)
    if not kv:
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
    sched_mem_gb = parse_tres_mem_gb(cfg_tres) or mem_gb
    allocated_mem_gb = parse_tres_mem_gb(alloc_tres)
    sched_free_mem_gb = max(sched_mem_gb - allocated_mem_gb, 0) if sched_mem_gb else free_mem_gb
    positive_mem_values = [value for value in (free_mem_gb, sched_free_mem_gb) if value > 0]
    usable_mem_gb = min(positive_mem_values) if positive_mem_values else 0
    cpus = parse_int(kv.get("CPUTot") or kv.get("CPUs"))
    allocated_cpus = parse_tres_int(alloc_tres, "cpu")
    free_cpus = max(cpus - allocated_cpus, 0) if cpus else 0
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
                usable_mem_gb=usable_mem_gb,
                cpus=cpus,
                free_cpus=free_cpus,
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


def parse_counts(value: str | None) -> List[int]:
    if not value:
        return []
    counts: List[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            count = int(part)
        except ValueError as exc:
            raise SystemExit(f"Invalid --counts value: {part!r}") from exc
        if count < 1:
            raise SystemExit("--counts values must be >= 1")
        if count not in counts:
            counts.append(count)
    return sorted(counts, reverse=True)


def default_counts(args: argparse.Namespace) -> List[int]:
    explicit = parse_counts(args.counts)
    if explicit:
        return explicit
    if args.request_gpus:
        return list(range(args.request_gpus, args.min_gpus - 1, -1))
    return [8, 7, 6, 4, 3, 2]


def preferred_partition_bonus(partition: str, args: argparse.Namespace) -> int:
    preferred = [part.strip() for part in args.prefer_partitions.split(",") if part.strip()]
    if partition not in preferred:
        return 0
    return (len(preferred) - preferred.index(partition)) * 10_000


def request_flags_for_partition(partition: str) -> str:
    if partition == "scavenger":
        return "-A scavenger --qos=scavenger "
    if partition == "cml-scavenger":
        return "-A cml-scavenger --qos=cml-scavenger "
    if partition == "class":
        return "-A class --qos=medium "
    if partition == "nexus":
        return "-A nexus --qos=medium "
    if partition == "cml-dpart":
        return "-A cml --qos=cml-default "
    if partition == "cml-furongh":
        return "-A cml-furongh --qos=cml-default "
    return ""


def is_idle_state(state: str) -> bool:
    normalized = state.upper()
    return "IDLE" in normalized and "MIX" not in normalized and "ALLOC" not in normalized


def format_salloc(option: AllocationOption, args: argparse.Namespace) -> str:
    return format_salloc_with_time(option, args, args.time)


def format_salloc_with_time(option: AllocationOption, args: argparse.Namespace, time_limit: str) -> str:
    row = option.candidate
    flags = request_flags_for_partition(row.partition)
    mem_gb = template_mem_gb(option, args)
    return (
        f"salloc -p {row.partition} {flags}--nodelist={row.node} "
        f"--gres=gpu:{row.gpu_type}:{option.requested} "
        f"--cpus-per-task={args.cpus} --mem={mem_gb}G --time={time_limit}"
    )


def template_mem_gb(option: AllocationOption, args: argparse.Namespace) -> int:
    if args.template_mem_gb != "auto":
        return parse_int(args.template_mem_gb)
    safe_max = max(option.candidate.usable_mem_gb - args.mem_headroom_gb, args.min_mem_gb)
    if args.max_template_mem_gb:
        safe_max = min(safe_max, args.max_template_mem_gb)
    return max(safe_max, 1)


def collect_candidates(args: argparse.Namespace) -> List[Candidate]:
    partitions = {item.strip() for item in (args.partitions or "").split(",") if item.strip()}
    counts = default_counts(args)
    min_free = min(counts) if counts else args.min_gpus
    fmt = "%N|%P|%T|%80G|%m|%c|%l"
    rows = run_text(["sinfo", "-N", "-h", "-o", fmt]).splitlines()
    details_by_node = collect_node_details()
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
        for candidate in node_candidates(node, partition, state, time_limit, details_by_node):
            key = (candidate.node, candidate.partition, candidate.gpu_type)
            if key in seen:
                continue
            seen.add(key)
            if candidate.free < min_free:
                continue
            if not state_is_usable(candidate.state, include_planned=args.include_planned, include_drain=args.include_drain):
                continue
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def expand_options(candidates: Iterable[Candidate], args: argparse.Namespace) -> List[AllocationOption]:
    counts = default_counts(args)
    options: List[AllocationOption] = []
    for candidate in candidates:
        if not args.ignore_fit and candidate.usable_mem_gb < args.min_mem_gb:
            continue
        if not args.ignore_fit and candidate.free_cpus < args.cpus:
            continue
        candidate_counts = counts or [candidate.free]
        for count in candidate_counts:
            if count <= candidate.free:
                options.append(
                    AllocationOption(
                        candidate=candidate,
                        requested=count,
                        rank_mode=args.rank_mode,
                        partition_bonus=preferred_partition_bonus(candidate.partition, args),
                        memory_weight=args.mem_weight,
                        memory_score_cap_gb=args.mem_score_cap_gb,
                    )
                )
    return sorted(options, key=lambda item: item.score, reverse=True)


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


def print_table(options: Iterable[AllocationOption], args: argparse.Namespace) -> None:
    rows = list(options)[: args.top]
    if not rows:
        print("No matching free GPU candidates found.")
        print("Try --mem-gb 40, --cpus 8, --include-planned, or omit --partitions.")
        return
    header = (
        f"{'#':>2} {'gpu_est':>7} {'request':>7} {'node':<12} {'partition':<16} {'state':<18} "
        f"{'gpu':<14} {'free/total':>10} {'usable':>7} {'free_mem':>8} {'mem_req':>7} {'free_cpu':>8} {'time':>10}"
    )
    print(header)
    print("-" * len(header))
    for index, option in enumerate(rows, start=1):
        row = option.candidate
        est = row.strength * option.requested
        print(
            f"{index:>2} {est:>7} {option.requested:>7} {row.node:<12} {row.partition:<16} {row.state:<18} "
            f"{row.gpu_type:<14} {row.free:>4}/{row.total:<5} {row.usable_mem_gb:>5}G {row.free_mem_gb:>6}G "
            f"{template_mem_gb(option, args):>5}G {row.free_cpus:>4}/{row.cpus:<3} {row.time_limit:>10}"
        )
    best = rows[0].candidate
    print()
    print("== Best immediate request template ==")
    print(format_salloc(rows[0], args))
    if request_flags_for_partition(best.partition):
        print("# Account/QoS flags were inferred from common UMIACS/Nexus associations.")
    else:
        print("# No account/QoS rule is known for this partition; add -A/--qos manually or prefer a scavenger row.")
    if not is_idle_state(best.state):
        print("# Top row is not fully IDLE; if it queues, try the fully IDLE fallback below.")
    idle_fallback = next((option for option in rows if is_idle_state(option.candidate.state)), None)
    if idle_fallback and idle_fallback != rows[0]:
        print()
        print("== Best fully IDLE fallback template ==")
        print(format_salloc(idle_fallback, args))
        print("# This may be less powerful but is often more likely to allocate immediately.")
    print("# gpu_est is per-GPU rank x requested GPUs; final ranking also includes a usable-memory bonus.")
    print("# usable memory is min(OS FreeMem, Slurm unallocated memory); mem_req is auto-sized unless --template-mem-gb is set.")
    print("# Rows are filtered by requested free CPU/min-memory unless --ignore-fit is used.")
    if args.fast_time and args.fast_time != args.time:
        print()
        print("== Shorter backfill alternative for the same top row ==")
        print(format_salloc_with_time(rows[0], args, args.fast_time))
        print("# Use this only if you prefer faster queue admission and are okay resuming later.")
    print("# If a request still queues: squeue -j JOBID -o '%.18i %.20P %.8T %.30R %.20S'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-gpus", type=int, default=1, help="Minimum free GPUs of the same type on one node.")
    parser.add_argument(
        "--request-gpus",
        type=int,
        default=None,
        help="Preferred GPU count. If --counts is omitted, compare this count down to --min-gpus.",
    )
    parser.add_argument(
        "--counts",
        default=None,
        help="Comma-separated allocation sizes to compare. Default: 8,7,6,4,3,2 unless --request-gpus is set.",
    )
    parser.add_argument(
        "--rank-mode",
        choices=("throughput", "single-gpu"),
        default="throughput",
        help="throughput compares GPU type x requested count; single-gpu prioritizes strongest individual GPUs.",
    )
    parser.add_argument(
        "--prefer-partitions",
        default="cml-scavenger,scavenger,cml-dpart,class,cml-furongh,cml,nexus",
        help="Comma-separated tie-break preference for requestable partitions.",
    )
    parser.add_argument("--cpus", type=int, default=16, help="CPU count required by the request template.")
    parser.add_argument(
        "--min-mem-gb",
        "--mem-gb",
        dest="min_mem_gb",
        type=int,
        default=60,
        help="Minimum usable memory in GB required to include a row. Alias: --mem-gb.",
    )
    parser.add_argument(
        "--template-mem-gb",
        default="auto",
        help="Memory in GB to put in salloc templates, or auto to request the largest safe amount.",
    )
    parser.add_argument(
        "--mem-headroom-gb",
        type=int,
        default=4,
        help="When --template-mem-gb=auto, leave this many GB unrequested for scheduling safety.",
    )
    parser.add_argument(
        "--max-template-mem-gb",
        type=int,
        default=0,
        help="Optional cap for auto template memory. Default 0 means no cap.",
    )
    parser.add_argument(
        "--mem-weight",
        type=int,
        default=5000,
        help="Ranking bonus per usable GB, after GPU score. Increase to prefer roomier nodes.",
    )
    parser.add_argument(
        "--mem-score-cap-gb",
        type=int,
        default=256,
        help="Cap usable-memory contribution to ranking so memory does not swamp GPU class/count.",
    )
    parser.add_argument("--time", default="1-00:00:00", help="Time limit to put in the main request template.")
    parser.add_argument(
        "--fast-time",
        default="12:00:00",
        help="Optional shorter backfill alternative printed for the top row. Set empty to suppress.",
    )
    parser.add_argument(
        "--ignore-fit",
        action="store_true",
        help="Do not filter rows by currently free CPU/memory. Useful for queue planning, not immediate allocation.",
    )
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
    if args.request_gpus is not None and args.request_gpus < 1:
        raise SystemExit("--request-gpus must be >= 1")
    if args.cpus < 1:
        raise SystemExit("--cpus must be >= 1")
    if args.min_mem_gb < 1:
        raise SystemExit("--min-mem-gb must be >= 1")
    if args.template_mem_gb != "auto" and parse_int(args.template_mem_gb) < 1:
        raise SystemExit("--template-mem-gb must be 'auto' or an integer >= 1")
    if args.mem_headroom_gb < 0:
        raise SystemExit("--mem-headroom-gb must be >= 0")
    if args.max_template_mem_gb < 0:
        raise SystemExit("--max-template-mem-gb must be >= 0")
    if args.mem_weight < 0:
        raise SystemExit("--mem-weight must be >= 0")
    if args.mem_score_cap_gb < 1:
        raise SystemExit("--mem-score-cap-gb must be >= 1")
    if not args.no_assoc:
        print_associations()
    candidates = collect_candidates(args)
    options = expand_options(candidates, args)
    print_table(options, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
