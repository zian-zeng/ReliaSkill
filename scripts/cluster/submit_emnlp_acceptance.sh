#!/usr/bin/env bash
set -euo pipefail

CONFIG="configs/experiments/emnlp_acceptance.yaml"
GPUS="4"
OUTPUT_ROOT=""
FORCE_PACKAGES="0"
SKIP_PACKAGES="0"
SKIP_ROUTING="0"
WALLTIME="12:00:00"
RUN_MODE="per-model"
MODELS="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --gpus) GPUS="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --force-packages) FORCE_PACKAGES="1"; shift ;;
    --skip-packages) SKIP_PACKAGES="1"; shift ;;
    --skip-routing) SKIP_ROUTING="1"; shift ;;
    --walltime) WALLTIME="$2"; shift 2 ;;
    --models) MODELS="$2"; shift 2 ;;
    --per-model) RUN_MODE="per-model"; shift ;;
    --all-models-per-shard) RUN_MODE="all-models-per-shard"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$GPUS" -lt 1 || "$GPUS" -gt 4 ]]; then
  echo "--gpus must be between 1 and 4 for the A5000 cluster profile" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"
mkdir -p logs

PACKAGE_ARGS=(--export=ALL,CONFIG="$CONFIG",FORCE_PACKAGES="$FORCE_PACKAGES")
SHARD_EXPORT="ALL,CONFIG=${CONFIG},NUM_SHARDS=${GPUS},SKIP_ROUTING=${SKIP_ROUTING}"
MERGE_EXPORT="ALL,CONFIG=${CONFIG}"
if [[ -n "$OUTPUT_ROOT" ]]; then
  PACKAGE_ARGS=(--export=ALL,CONFIG="$CONFIG",OUTPUT_ROOT="$OUTPUT_ROOT",FORCE_PACKAGES="$FORCE_PACKAGES")
  SHARD_EXPORT="${SHARD_EXPORT},OUTPUT_ROOT=${OUTPUT_ROOT}"
  MERGE_EXPORT="${MERGE_EXPORT},OUTPUT_ROOT=${OUTPUT_ROOT}"
fi

if [[ "$SKIP_PACKAGES" == "1" ]]; then
  package_job=""
  dependency_arg=()
  echo "package_job=skipped"
else
  package_job="$(sbatch --parsable "${PACKAGE_ARGS[@]}" "${SCRIPT_DIR}/build_shared_packages.sbatch")"
  dependency_arg=(--dependency=afterok:${package_job})
  echo "package_job=${package_job}"
fi

if [[ "$RUN_MODE" == "per-model" ]]; then
  mapfile -t MODEL_FILTERS < <("${PYTHON_BIN:-python}" scripts/list_config_models.py --config "$CONFIG" --models "$MODELS" --format slug)
  if [[ "${#MODEL_FILTERS[@]}" -eq 0 ]]; then
    echo "No configured models matched --models=${MODELS}" >&2
    exit 2
  fi
  shard_jobs=()
  for model_filter in "${MODEL_FILTERS[@]}"; do
    model_export="${SHARD_EXPORT},MODELS=${model_filter}"
    shard_job="$(sbatch --parsable "${dependency_arg[@]}" --array=0-$((GPUS - 1))%${GPUS} --gres=gpu:1 --time="${WALLTIME}" --export="${model_export}" "${SCRIPT_DIR}/run_emnlp_shard.sbatch")"
    shard_jobs+=("${shard_job}")
    echo "shard_job_${model_filter}=${shard_job}"
  done
  dependency_ids="$(IFS=:; echo "${shard_jobs[*]}")"
  merge_job="$(sbatch --parsable --dependency=afterok:${dependency_ids} --export="${MERGE_EXPORT}" "${SCRIPT_DIR}/merge_emnlp_shards.sbatch")"
else
  shard_job="$(sbatch --parsable "${dependency_arg[@]}" --array=0-$((GPUS - 1))%${GPUS} --gres=gpu:1 --time="${WALLTIME}" --export="${SHARD_EXPORT},MODELS=${MODELS}" "${SCRIPT_DIR}/run_emnlp_shard.sbatch")"
  echo "shard_job=${shard_job}"
  merge_job="$(sbatch --parsable --dependency=afterok:${shard_job} --export="${MERGE_EXPORT}" "${SCRIPT_DIR}/merge_emnlp_shards.sbatch")"
fi
echo "merge_job=${merge_job}"
