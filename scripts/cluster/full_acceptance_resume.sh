#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-help}"
CONFIG="${CONFIG:-configs/experiments/emnlp_acceptance.yaml}"
GPUS="${GPUS:-4}"
MODELS="${MODELS:-all}"
PYTHON_BIN="${PYTHON_BIN:-python}"
LOG_DIR="${LOG_DIR:-logs/full_acceptance}"
GPU_BUDGET_GB="${GPU_BUDGET_GB:-24}"

mkdir -p "$LOG_DIR" outputs/reports outputs/tables

usage() {
  cat <<EOF
Usage: $0 <action>

Actions:
  plan            Write and print the full-run scheduler plan.
  build-packages  Build shared packages once. Uses dev controls only where configured.
  check-packages  Fail if any required shared package is missing.
  start           Start/resume all configured models across GPUS detached from Ctrl-C.
  supervise       Internal foreground worker used by start.
  status          Show worker status, result counts, and recent errors.
  monitor         Show the Rich progress dashboard.
  merge           Merge completed shard outputs and write tables.

Environment:
  CONFIG=$CONFIG
  GPUS=$GPUS
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
  plan
  check_packages
  pids=()
  for shard in $(seq 0 $((GPUS - 1))); do
    (
      export CUDA_VISIBLE_DEVICES="$shard"
      export PYTHONUNBUFFERED=1
      exec "$PYTHON_BIN" scripts/run_cluster_shard.py \
        --config "$CONFIG" \
        --shard-index "$shard" \
        --num-shards "$GPUS" \
        --models "$MODELS"
    ) > "$LOG_DIR/shard_${shard}.out" 2> "$LOG_DIR/shard_${shard}.err" &
    pid="$!"
    echo "$pid" > "$LOG_DIR/shard_${shard}.pid"
    pids+=("$pid")
    echo "started_shard_${shard}_pid=${pid} gpu=${shard}"
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

start() {
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
}

monitor() {
  "$PYTHON_BIN" scripts/monitor_experiment_progress.py \
    --config "$CONFIG" \
    --num-shards "$GPUS" \
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
