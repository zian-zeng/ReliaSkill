#!/usr/bin/env bash
set -euo pipefail

CONFIG="configs/experiments/emnlp_acceptance.yaml"
GPUS="4"
OUTPUT_ROOT=""
FORCE_PACKAGES="0"
SKIP_ROUTING="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --gpus) GPUS="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --force-packages) FORCE_PACKAGES="1"; shift ;;
    --skip-routing) SKIP_ROUTING="1"; shift ;;
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

package_job="$(sbatch --parsable "${PACKAGE_ARGS[@]}" "${SCRIPT_DIR}/build_shared_packages.sbatch")"
shard_job="$(sbatch --parsable --dependency=afterok:${package_job} --array=0-$((GPUS - 1))%${GPUS} --gres=gpu:1 --export="${SHARD_EXPORT}" "${SCRIPT_DIR}/run_emnlp_shard.sbatch")"
merge_job="$(sbatch --parsable --dependency=afterok:${shard_job} --export="${MERGE_EXPORT}" "${SCRIPT_DIR}/merge_emnlp_shards.sbatch")"

echo "package_job=${package_job}"
echo "shard_job=${shard_job}"
echo "merge_job=${merge_job}"
