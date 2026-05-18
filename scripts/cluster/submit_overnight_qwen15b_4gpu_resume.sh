#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-configs/experiments/overnight_qwen15b_4gpu_resume.yaml}"
GPUS="${GPUS:-4}"
WALLTIME="${WALLTIME:-08:30:00}"
MODELS="${MODELS:-Qwen_Qwen2.5-1.5B-Instruct}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

python scripts/plan_experiment_run.py \
  --config "$CONFIG" \
  --gpu_budget_gb 24 \
  --strict \
  --json \
  --output-report outputs/reports/overnight_qwen15b_4gpu_pre_submit_plan.md \
  --output-csv outputs/tables/overnight_qwen15b_4gpu_pre_submit_plan.csv

bash scripts/cluster/submit_emnlp_acceptance.sh \
  --config "$CONFIG" \
  --gpus "$GPUS" \
  --models "$MODELS" \
  --walltime "$WALLTIME" \
  --skip-packages \
  --per-model

echo
echo "Monitor with:"
echo "python scripts/monitor_experiment_progress.py --config $CONFIG --num-shards $GPUS --models $MODELS"
