#!/usr/bin/env bash
set -euo pipefail

echo "host=$(hostname)"
echo "user=${USER:-unknown}"
echo

echo "== CML partitions =="
if command -v sinfo >/dev/null 2>&1; then
  sinfo -p cml-dpart,cml-scavenger,cml-cpu -o "%20P %8D %10t %24G %10m %8c %12l %N" || true
else
  echo "sinfo not found; run this on a Nexus/CML login node."
fi
echo

echo "== GPU node details =="
if command -v sinfo >/dev/null 2>&1; then
  sinfo -p cml-dpart,cml-scavenger -N -o "%20N %12P %10t %24G %10m %8c %12l" || true
fi
echo

echo "== Associations for current user =="
if command -v sacctmgr >/dev/null 2>&1; then
  sacctmgr -n -P show assoc user="${USER:-}" format=Account,Partition,QOS%40,GrpTRES%60,MaxJobs 2>/dev/null || true
else
  echo "sacctmgr not found."
fi
echo

echo "== Current CML queue pressure =="
if command -v squeue >/dev/null 2>&1; then
  squeue -p cml-dpart,cml-scavenger -o "%.18i %.9P %.24j %.8u %.2t %.10M %.10l %.6D %R" || true
fi
echo

cat <<'EOF'
Suggested ReliaSkill profiles:

1. Guaranteed pilot or short run:
   PARTITION=cml-dpart QOS=cml-medium ACCOUNT=<your-cml-account> GPUS=4 WALLTIME=12:00:00

2. Resume-safe long replication, if the queue has idle scavenger GPUs:
   PARTITION=cml-scavenger QOS=cml-scavenger ACCOUNT=cml-scavenger GPUS=8 WALLTIME=3-00:00:00

Use the largest GPUS value that appears on one available node in the GPU node details.
ReliaSkill shard outputs are resume-safe, so scavenger preemption is acceptable for long runs.
EOF
