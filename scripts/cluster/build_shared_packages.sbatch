#!/usr/bin/env bash
#SBATCH --job-name=reliaskill-packages
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --output=logs/reliaskill-packages-%j.out
#SBATCH --error=logs/reliaskill-packages-%j.err

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
CONFIG="${CONFIG:-configs/experiments/emnlp_acceptance.yaml}"
FORCE_PACKAGES="${FORCE_PACKAGES:-0}"
OUTPUT_ROOT="${OUTPUT_ROOT:-}"

mkdir -p logs

args=(scripts/build_shared_skill_packages.py --config "$CONFIG" --json)
if [[ "$FORCE_PACKAGES" == "1" ]]; then
  args+=(--force)
fi
if [[ -n "$OUTPUT_ROOT" ]]; then
  args+=(--output-root "$OUTPUT_ROOT")
fi

"$PYTHON_BIN" "${args[@]}"
