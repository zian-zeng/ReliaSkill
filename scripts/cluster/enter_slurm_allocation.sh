#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/cluster/enter_slurm_allocation.sh [options] [-- command ...]

Find the newest running Slurm GPU allocation for the current user and enter it
with srun --pty. By default this drops you into the ReliaSkill project directory
and wires PYTHON_BIN to the project conda-style Python.

Options:
  --jobid JOBID          Enter this allocation directly.
  --partition NAME       Only consider running jobs in this partition.
  --any                  Consider non-GPU running jobs too.
  --list                 List candidate allocations and exit.
  --plain                Do not set ReliaSkill env; just enter bash -l.
  --project-dir DIR      Project directory on the cluster.
                         Default: /fs/cml-scratch/zianzeng/ReliaSkill
  --env-dir DIR          Python environment directory.
                         Default: /nfshomes/zianzeng/envs/reliaskill-py311
  -h, --help             Show this help.

Examples:
  scripts/cluster/enter_slurm_allocation.sh
  scripts/cluster/enter_slurm_allocation.sh --list
  scripts/cluster/enter_slurm_allocation.sh --jobid 6866473
  scripts/cluster/enter_slurm_allocation.sh -- nvidia-smi
EOF
}

jobid=""
partition_filter=""
include_any=0
list_only=0
plain=0
project_dir="${RELIASKILL_PROJECT_DIR:-/fs/cml-scratch/zianzeng/ReliaSkill}"
env_dir="${RELIASKILL_ENV:-/nfshomes/zianzeng/envs/reliaskill-py311}"
cmd=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jobid)
      jobid="${2:-}"
      shift 2
      ;;
    --partition)
      partition_filter="${2:-}"
      shift 2
      ;;
    --any)
      include_any=1
      shift
      ;;
    --list)
      list_only=1
      shift
      ;;
    --plain)
      plain=1
      shift
      ;;
    --project-dir)
      project_dir="${2:-}"
      shift 2
      ;;
    --env-dir)
      env_dir="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      cmd=("$@")
      break
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 127
  fi
}

collect_candidates() {
  local line id partition nodes name elapsed detail
  squeue -h -u "$USER" -t RUNNING -o "%i|%P|%N|%j|%M" |
    while IFS='|' read -r id partition nodes name elapsed; do
      [[ -n "${id:-}" ]] || continue
      if [[ -n "$partition_filter" && "$partition" != "$partition_filter" ]]; then
        continue
      fi
      if [[ "$include_any" -eq 0 ]]; then
        detail="$(scontrol show job "$id" -o 2>/dev/null || true)"
        if [[ "$detail" != *gpu* && "$detail" != *GRES* ]]; then
          continue
        fi
      fi
      printf '%s|%s|%s|%s|%s\n' "$id" "$partition" "$nodes" "$name" "$elapsed"
    done
}

print_candidates() {
  local candidates="$1"
  if [[ -z "$candidates" ]]; then
    echo "No running matching Slurm allocations found."
    return
  fi
  printf '%-12s %-18s %-20s %-24s %-10s\n' "JOBID" "PARTITION" "NODELIST" "NAME" "ELAPSED"
  printf '%s\n' "$candidates" |
    sort -t'|' -k1,1nr |
    awk -F'|' '{printf "%-12s %-18s %-20s %-24s %-10s\n", $1, $2, $3, $4, $5}'
}

require_cmd squeue
require_cmd srun
require_cmd scontrol

if [[ -n "$jobid" ]]; then
  if ! scontrol show job "$jobid" >/dev/null 2>&1; then
    echo "No such Slurm job: $jobid" >&2
    exit 1
  fi
elif [[ -n "${SLURM_JOB_ID:-}" && "$include_any" -eq 1 ]]; then
  jobid="$SLURM_JOB_ID"
else
  candidates="$(collect_candidates)"
  if [[ "$list_only" -eq 1 ]]; then
    print_candidates "$candidates"
    exit 0
  fi
  if [[ -z "$candidates" ]]; then
    echo "No running GPU allocation found for user $USER." >&2
    echo "Current jobs:" >&2
    squeue -u "$USER" -o "%.18i %.9T %.20P %.30R %.30N" >&2 || true
    exit 1
  fi
  jobid="$(printf '%s\n' "$candidates" | sort -t'|' -k1,1nr | head -n1 | cut -d'|' -f1)"
  echo "Selected newest running GPU allocation: $jobid"
  print_candidates "$(printf '%s\n' "$candidates" | grep "^${jobid}|")"
fi

if [[ "$plain" -eq 1 ]]; then
  if [[ "${#cmd[@]}" -gt 0 ]]; then
    exec srun --jobid "$jobid" --pty "${cmd[@]}"
  fi
  exec srun --jobid "$jobid" --pty bash -l
fi

export RELIASKILL_PROJECT_DIR="$project_dir"
export RELIASKILL_ENV="$env_dir"
export_arg="ALL,RELIASKILL_PROJECT_DIR=${RELIASKILL_PROJECT_DIR},RELIASKILL_ENV=${RELIASKILL_ENV}"

if [[ "${#cmd[@]}" -gt 0 ]]; then
  exec srun --jobid "$jobid" --export="$export_arg" --pty "${cmd[@]}"
fi

exec srun --jobid "$jobid" --export="$export_arg" --pty bash -lc '
  cd "$RELIASKILL_PROJECT_DIR"
  export PATH="$RELIASKILL_ENV/bin:$PATH"
  export LD_LIBRARY_PATH="$RELIASKILL_ENV/lib:${LD_LIBRARY_PATH:-}"
  export PYTHON_BIN="$RELIASKILL_ENV/bin/python3.11"
  echo "[ReliaSkill] entered $(hostname) via SLURM_JOB_ID=${SLURM_JOB_ID:-unknown}"
  echo "[ReliaSkill] project: $PWD"
  echo "[ReliaSkill] python: $PYTHON_BIN"
  exec bash
'
