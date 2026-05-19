#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-configs/experiments/overnight_qwen15b_full_method_pilot.yaml}"
GPUS="${GPUS:-4}"
CPUS="${CPUS:-16}"
MEM="${MEM:-128G}"
QOS="${QOS-high}"
ACCOUNT="${ACCOUNT-}"
PARTITION="${PARTITION-}"
WALLTIME="${WALLTIME:-1-00:00:00}"
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

sbatch_args=(--parsable)
if [[ -n "$ACCOUNT" ]]; then
  sbatch_args+=(--account="$ACCOUNT")
fi
if [[ -n "$PARTITION" ]]; then
  sbatch_args+=(--partition="$PARTITION")
fi
if [[ -n "$QOS" ]]; then
  sbatch_args+=(--qos="$QOS")
fi
sbatch_args+=(
  --cpus-per-task="$CPUS"
  --mem="$MEM"
  --gres="gpu:${GPUS}"
  --time="$WALLTIME"
  --export=ALL,CONFIG="$CONFIG",GPUS="$GPUS",MODELS="$MODELS"
  scripts/cluster/run_overnight_qwen15b_4gpu_resume.sbatch
)

echo "submitting account=${ACCOUNT:-<cluster-default>} partition=${PARTITION:-<cluster-default>} qos=${QOS:-<cluster-default>} gpus=${GPUS}"
job_id="$(sbatch "${sbatch_args[@]}")"

echo
echo "overnight_job=${job_id}"
echo "Monitor with:"
echo "python scripts/monitor_experiment_progress.py --config $CONFIG --num-shards $GPUS --models $MODELS"
