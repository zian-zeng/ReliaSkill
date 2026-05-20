#!/usr/bin/env bash
#SBATCH --job-name=reliaskill-overnight-qwen15b
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --gres=gpu:4
#SBATCH --time=1-00:00:00
#SBATCH --output=logs/reliaskill-overnight-qwen15b-%j.out
#SBATCH --error=logs/reliaskill-overnight-qwen15b-%j.err

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
CONFIG="${CONFIG:-configs/experiments/overnight_qwen15b_full_method_pilot.yaml}"
GPUS="${GPUS:-4}"
MODELS="${MODELS:-Qwen_Qwen2.5-1.5B-Instruct}"
GPU_BUDGET_GB="${GPU_BUDGET_GB:-24}"
PLAN_SLUG="$(basename "$CONFIG" .yaml)"

mkdir -p logs

"$PYTHON_BIN" scripts/plan_experiment_run.py \
  --config "$CONFIG" \
  --gpu_budget_gb "$GPU_BUDGET_GB" \
  --strict \
  --json \
  --output-report "outputs/reports/${PLAN_SLUG}_${GPUS}gpu_in_job_plan.md" \
  --output-csv "outputs/tables/${PLAN_SLUG}_${GPUS}gpu_in_job_plan.csv"

pids=()
for shard_index in $(seq 0 $((GPUS - 1))); do
  shard_log="logs/${PLAN_SLUG}-${SLURM_JOB_ID:-manual}-shard-${shard_index}.out"
  shard_err="logs/${PLAN_SLUG}-${SLURM_JOB_ID:-manual}-shard-${shard_index}.err"
  (
    export CUDA_VISIBLE_DEVICES="$shard_index"
    "$PYTHON_BIN" scripts/run_cluster_shard.py \
      --config "$CONFIG" \
      --shard-index "$shard_index" \
      --num-shards "$GPUS" \
      --models "$MODELS"
  ) >"$shard_log" 2>"$shard_err" &
  pid="$!"
  pids+=("$pid")
  echo "started_shard_${shard_index}_pid=${pid} gpu=${shard_index} log=${shard_log}"
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    status=1
  fi
done

if [[ "$status" -ne 0 ]]; then
  echo "At least one shard failed; not merging. Check logs/${PLAN_SLUG}-${SLURM_JOB_ID:-manual}-shard-*.err" >&2
  exit "$status"
fi

"$PYTHON_BIN" scripts/merge_cluster_shards.py --config "$CONFIG"
