#!/usr/bin/env bash
#SBATCH --job-name=reliaskill-overnight-qwen15b
#SBATCH --qos=high
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

mkdir -p logs

"$PYTHON_BIN" scripts/plan_experiment_run.py \
  --config "$CONFIG" \
  --gpu_budget_gb 24 \
  --strict \
  --json \
  --output-report outputs/reports/overnight_qwen15b_4gpu_pre_submit_plan.md \
  --output-csv outputs/tables/overnight_qwen15b_4gpu_pre_submit_plan.csv

pids=()
for shard_index in $(seq 0 $((GPUS - 1))); do
  shard_log="logs/reliaskill-overnight-qwen15b-${SLURM_JOB_ID:-manual}-shard-${shard_index}.out"
  shard_err="logs/reliaskill-overnight-qwen15b-${SLURM_JOB_ID:-manual}-shard-${shard_index}.err"
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
  echo "At least one shard failed; not merging. Check logs/reliaskill-overnight-qwen15b-${SLURM_JOB_ID:-manual}-shard-*.err" >&2
  exit "$status"
fi

"$PYTHON_BIN" scripts/merge_cluster_shards.py --config "$CONFIG"
