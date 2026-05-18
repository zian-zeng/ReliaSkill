#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-help}"
CONFIG="${CONFIG:-configs/experiments/emnlp_acceptance.yaml}"
GPUS="${GPUS:-4}"
TOTAL_SHARDS="${TOTAL_SHARDS:-32}"
MODELS="${MODELS:-all}"
PYTHON_BIN="${PYTHON_BIN:-python}"
LOG_DIR="${LOG_DIR:-logs/full_acceptance}"
GPU_BUDGET_GB="${GPU_BUDGET_GB:-24}"
CLAIM_DIR="$LOG_DIR/shard_claims"
STOP_FILE="$LOG_DIR/STOP"

mkdir -p "$LOG_DIR" outputs/reports outputs/tables

usage() {
  cat <<EOF
Usage: $0 <action>

Actions:
  plan            Write and print the full-run scheduler plan.
  build-packages  Build shared packages once. Uses dev controls only where configured.
  check-packages  Fail if any required shared package is missing.
  start           Start/resume TOTAL_SHARDS with GPUS concurrent workers detached from Ctrl-C.
  supervise       Internal foreground worker used by start.
  status          Show worker status, result counts, and recent errors.
  monitor         Show the Rich progress dashboard.
  merge           Merge completed shard outputs and write tables.

Environment:
  CONFIG=$CONFIG
  GPUS=$GPUS
  TOTAL_SHARDS=$TOTAL_SHARDS
  MODELS=$MODELS
  LOG_DIR=$LOG_DIR
EOF
}

plan() {
  "$PYTHON_BIN" scripts/plan_experiment_run.py \
    --config "$CONFIG" \
    --gpu_budget_gb "$GPU_BUDGET_GB" \
    --strict \
    --json \
    --output-report outputs/reports/full_acceptance_pre_submit_plan.md \
    --output-csv outputs/tables/full_acceptance_pre_submit_plan.csv
}

build_packages() {
  "$PYTHON_BIN" scripts/build_shared_skill_packages.py \
    --config "$CONFIG" \
    --json | tee "$LOG_DIR/build_shared_packages.json"
}

check_packages() {
  "$PYTHON_BIN" scripts/check_shared_skill_packages.py \
    --config "$CONFIG" \
    --json | tee "$LOG_DIR/check_shared_packages.json"
}

supervise() {
  if [[ "$TOTAL_SHARDS" -lt "$GPUS" ]]; then
    echo "TOTAL_SHARDS must be >= GPUS to keep the worker pool saturated." >&2
    exit 2
  fi
  plan
  check_packages
  rm -rf "$CLAIM_DIR"
  mkdir -p "$CLAIM_DIR"
  rm -f "$STOP_FILE"
  pids=()
  for gpu in $(seq 0 $((GPUS - 1))); do
    worker "$gpu" > "$LOG_DIR/worker_gpu_${gpu}.out" 2> "$LOG_DIR/worker_gpu_${gpu}.err" &
    pid="$!"
    echo "$pid" > "$LOG_DIR/worker_gpu_${gpu}.pid"
    pids+=("$pid")
    echo "started_worker_gpu_${gpu}_pid=${pid}"
  done

  status=0
  for pid in "${pids[@]}"; do
    wait "$pid" || status=1
  done
  if [[ "$status" -ne 0 ]]; then
    echo "One or more shards failed; not merging. Inspect $LOG_DIR/shard_*.err" >&2
    exit "$status"
  fi
  "$PYTHON_BIN" scripts/merge_cluster_shards.py --config "$CONFIG" \
    > "$LOG_DIR/merge.out" 2> "$LOG_DIR/merge.err"
}

worker() {
  local gpu="$1"
  local status=0
  for shard in $(seq 0 $((TOTAL_SHARDS - 1))); do
    if [[ -f "$STOP_FILE" ]]; then
      echo "gpu=${gpu} stopping because $STOP_FILE exists"
      break
    fi
    if ! mkdir "$CLAIM_DIR/shard_${shard}.claim" 2>/dev/null; then
      continue
    fi
    echo "gpu=${gpu} running shard=${shard}/${TOTAL_SHARDS}"
    if ! CUDA_VISIBLE_DEVICES="$gpu" PYTHONUNBUFFERED=1 "$PYTHON_BIN" scripts/run_cluster_shard.py \
      --config "$CONFIG" \
      --shard-index "$shard" \
      --num-shards "$TOTAL_SHARDS" \
      --models "$MODELS" \
      > "$LOG_DIR/shard_${shard}.out" 2> "$LOG_DIR/shard_${shard}.err"; then
      echo "gpu=${gpu} shard=${shard} failed; see $LOG_DIR/shard_${shard}.err" >&2
      touch "$STOP_FILE"
      status=1
      break
    fi
    echo "gpu=${gpu} finished shard=${shard}/${TOTAL_SHARDS}"
  done
  return "$status"
}

start() {
  if pgrep -f "run_cluster_shard.py --config ${CONFIG}" >/dev/null; then
    echo "Shard workers for this config already appear to be running. Use '$0 status' before starting another supervisor." >&2
    exit 1
  fi
  if ! check_packages >/dev/null; then
    echo "Shared packages are incomplete. Run:" >&2
    echo "  $0 build-packages" >&2
    echo "then retry:" >&2
    echo "  $0 start" >&2
    exit 1
  fi
  setsid "$0" supervise > "$LOG_DIR/supervisor.out" 2> "$LOG_DIR/supervisor.err" < /dev/null &
  supervisor_pid="$!"
  echo "$supervisor_pid" > "$LOG_DIR/supervisor.pid"
  disown "$supervisor_pid" 2>/dev/null || true
  echo "supervisor_pid=$supervisor_pid"
  echo "Monitor with:"
  echo "  $0 monitor"
}

status() {
  echo "config=$CONFIG"
  echo "models=$MODELS"
  echo "gpus=$GPUS"
  echo "total_shards=$TOTAL_SHARDS"
  if [[ -f "$LOG_DIR/supervisor.pid" ]]; then
    echo "supervisor:"
    ps -fp "$(cat "$LOG_DIR/supervisor.pid")" || true
  fi
  echo "workers:"
  pgrep -af "run_cluster_shard.py --config ${CONFIG}" || true
  echo "result_counts:"
  find outputs/emnlp_acceptance/predictors -name "*.result.json" 2>/dev/null | wc -l | awk '{print "benchmark_result_json=" $1}'
  find outputs/emnlp_acceptance/predictors -name "*.routing.json" 2>/dev/null | wc -l | awk '{print "routing_json=" $1}'
  find outputs/emnlp_acceptance/predictors -name "*.live_result.json" 2>/dev/null | wc -l | awk '{print "live_result_json=" $1}'
  echo "recent_errors:"
  tail -n 40 "$LOG_DIR"/shard_*.err 2>/dev/null || true
  echo "worker_logs:"
  tail -n 20 "$LOG_DIR"/worker_gpu_*.out 2>/dev/null || true
}

monitor() {
  "$PYTHON_BIN" scripts/monitor_experiment_progress.py \
    --config "$CONFIG" \
    --num-shards "$TOTAL_SHARDS" \
    --models "$MODELS"
}

merge() {
  "$PYTHON_BIN" scripts/merge_cluster_shards.py --config "$CONFIG"
}

case "$ACTION" in
  plan) plan ;;
  build-packages) build_packages ;;
  check-packages) check_packages ;;
  start) start ;;
  supervise) supervise ;;
  status) status ;;
  monitor) monitor ;;
  merge) merge ;;
  help|-h|--help) usage ;;
  *) echo "Unknown action: $ACTION" >&2; usage; exit 2 ;;
esac
