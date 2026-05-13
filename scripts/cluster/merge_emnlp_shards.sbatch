#!/usr/bin/env bash
#SBATCH --job-name=reliaskill-merge
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=logs/reliaskill-merge-%j.out
#SBATCH --error=logs/reliaskill-merge-%j.err

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
CONFIG="${CONFIG:-configs/experiments/emnlp_acceptance.yaml}"
OUTPUT_ROOT="${OUTPUT_ROOT:-}"

mkdir -p logs

args=(scripts/merge_cluster_shards.py --config "$CONFIG")
if [[ -n "$OUTPUT_ROOT" ]]; then
  args+=(--output-root "$OUTPUT_ROOT")
fi

"$PYTHON_BIN" "${args[@]}"
