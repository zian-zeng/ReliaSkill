#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-configs/experiments/reliaskill_v1_arbitration_upgrade_pilot_fast.yaml}"
GPUS="${GPUS:-4}"
CPUS="${CPUS:-16}"
MEM="${MEM:-128G}"
QOS="${QOS-high}"
ACCOUNT="${ACCOUNT-}"
PARTITION="${PARTITION-}"
WALLTIME="${WALLTIME:-12:00:00}"
MODELS="${MODELS:-Qwen_Qwen2.5-1.5B-Instruct}"
GPU_BUDGET_GB="${GPU_BUDGET_GB:-24}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p logs outputs/reports outputs/tables

plan_slug="$(basename "$CONFIG" .yaml)"
python scripts/plan_experiment_run.py \
  --config "$CONFIG" \
  --gpu_budget_gb "$GPU_BUDGET_GB" \
  --strict \
  --json \
  --output-report "outputs/reports/${plan_slug}_pre_submit_plan.md" \
  --output-csv "outputs/tables/${plan_slug}_pre_submit_plan.csv"

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
  --job-name="reliaskill-upgrade"
  --cpus-per-task="$CPUS"
  --mem="$MEM"
  --gres="gpu:${GPUS}"
  --time="$WALLTIME"
  --export=ALL,CONFIG="$CONFIG",GPUS="$GPUS",MODELS="$MODELS"
  scripts/cluster/run_overnight_qwen15b_4gpu_resume.sbatch
)

echo "submitting config=${CONFIG} models=${MODELS} gpus=${GPUS} walltime=${WALLTIME}"
job_id="$(sbatch "${sbatch_args[@]}")"

echo
echo "upgrade_job=${job_id}"
echo "Monitor with:"
echo "python scripts/monitor_experiment_progress.py --config $CONFIG --num-shards $GPUS --models $MODELS"
echo
echo "After completion:"
echo "python scripts/merge_cluster_shards.py --config $CONFIG"
