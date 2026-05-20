#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-guaranteed}"
CONFIG="${CONFIG:-configs/experiments/reliaskill_v1_arbitration_upgrade_pilot_fast.yaml}"
MODELS="${MODELS:-Qwen_Qwen2.5-1.5B-Instruct}"
GPUS="${GPUS:-4}"
GPU_BUDGET_GB="${GPU_BUDGET_GB:-24}"
CPUS="${CPUS:-16}"
MEM="${MEM:-128G}"
GPU_TYPE="${GPU_TYPE-}"
GPU_GRES="${GPU_GRES-}"

case "$PROFILE" in
  guaranteed|dpart)
    PARTITION="${PARTITION:-cml-dpart}"
    QOS="${QOS:-cml-medium}"
    ACCOUNT="${ACCOUNT:-cml}"
    WALLTIME="${WALLTIME:-12:00:00}"
    ;;
  scavenger)
    PARTITION="${PARTITION:-cml-scavenger}"
    QOS="${QOS:-cml-scavenger}"
    ACCOUNT="${ACCOUNT:-cml-scavenger}"
    WALLTIME="${WALLTIME:-3-00:00:00}"
    ;;
  *)
    echo "Unknown PROFILE=$PROFILE. Use PROFILE=guaranteed or PROFILE=scavenger." >&2
    exit 2
    ;;
esac

export CONFIG MODELS GPUS GPU_BUDGET_GB CPUS MEM PARTITION QOS ACCOUNT WALLTIME GPU_TYPE GPU_GRES

echo "CML profile: $PROFILE"
echo "config=$CONFIG"
echo "models=$MODELS"
echo "partition=$PARTITION qos=$QOS account=$ACCOUNT gpus=$GPUS gpu_budget_gb=$GPU_BUDGET_GB walltime=$WALLTIME"
if [[ -n "$GPU_GRES" ]]; then
  echo "gpu_gres=$GPU_GRES"
elif [[ -n "$GPU_TYPE" ]]; then
  echo "gpu_type=$GPU_TYPE"
fi
echo

bash scripts/cluster/submit_arbitration_upgrade_4gpu.sh
