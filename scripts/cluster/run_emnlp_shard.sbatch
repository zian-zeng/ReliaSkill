#!/usr/bin/env bash
#SBATCH --job-name=reliaskill-shard
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=72:00:00
#SBATCH --output=logs/reliaskill-shard-%A-%a.out
#SBATCH --error=logs/reliaskill-shard-%A-%a.err

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
CONFIG="${CONFIG:-configs/experiments/emnlp_acceptance.yaml}"
NUM_SHARDS="${NUM_SHARDS:-1}"
SKIP_ROUTING="${SKIP_ROUTING:-0}"
OUTPUT_ROOT="${OUTPUT_ROOT:-}"
SHARD_INDEX="${SLURM_ARRAY_TASK_ID:-0}"

mkdir -p logs

args=(
  scripts/run_cluster_shard.py
  --config "$CONFIG"
  --shard-index "$SHARD_INDEX"
  --num-shards "$NUM_SHARDS"
)
if [[ "$SKIP_ROUTING" == "1" ]]; then
  args+=(--skip-routing)
fi
if [[ -n "$OUTPUT_ROOT" ]]; then
  args+=(--output-root "$OUTPUT_ROOT")
fi

"$PYTHON_BIN" "${args[@]}"
