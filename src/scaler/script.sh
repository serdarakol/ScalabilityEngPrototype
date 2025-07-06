#!/usr/bin/env bash
set -euo pipefail

# Configuration
NS=prototype
SS_NAME=species

# Default target values for demonstration
TARGET_REPLICAS=${REPLICAS:-1}
BASE_CPU_REQUEST=${BASE_CPU_REQUEST:-200m}
BASE_MEM_REQUEST=${BASE_MEM_REQUEST:-256Mi}
BASE_CPU_LIMIT=${BASE_CPU_LIMIT:-500m}
BASE_MEM_LIMIT=${BASE_MEM_LIMIT:-512Mi}

sage() {
  echo "Usage: $0 [--replicas N] [--cpu CPU] [--memory MEM] [--restart]"
  echo "  --replicas N     Scale to N replicas"
  echo "  --cpu CPU        Set CPU request & limit (e.g. 200m)"
  echo "  --memory MEM     Set memory request & limit (e.g. 256Mi)"
  echo "  --restart        Rollout restart the StatefulSet after changes"
  exit 1
}

# Flags
REPLICAS=""
CPU=""
MEM=""
RESTART=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --replicas)
      REPLICAS=$2; shift 2;;
    --cpu)
      CPU=$2; shift 2;;
    --memory)
      MEM=$2; shift 2;;
    --restart)
      RESTART=true; shift;;
    *)
      usage;;
  esac
done

# 1) Horizontal scaling
if [[ -n "$REPLICAS" ]]; then
  echo "[SCALER] Scaling StatefulSet '$SS_NAME' in namespace '$NS' to $REPLICAS replicas"
  kubectl scale statefulset/$SS_NAME --replicas=$REPLICAS -n $NS
fi


# 2) Vertical scaling
if [[ -n "$CPU" || -n "$MEM" ]]; then
  echo "[SCALER] Updating resources on StatefulSet '$SS_NAME'"
  CMD=(kubectl set resources statefulset/$SS_NAME --containers=species-service)

  # CPU: request = CPU, limit = 2 * CPU
  if [[ -n "$CPU" ]]; then
    cpu_req="$CPU"
    if [[ "$CPU" =~ ^([0-9]+)m$ ]]; then
      val="${BASH_REMATCH[1]}"
      cpu_lim="${val}m"
      cpu_lim="$(($val * 2))m"
    else
      val="$CPU"
      cpu_lim="$(($val * 2))"
    fi
    CMD+=(--requests=cpu="$cpu_req" --limits=cpu="$cpu_lim")
  fi

  # Memory: request = MEM, limit = 2 * MEM
  if [[ -n "$MEM" ]]; then
    mem_req="$MEM"
    if [[ "$MEM" =~ ^([0-9]+)Mi$ ]]; then
      val="${BASH_REMATCH[1]}"
      mem_lim="$(($val * 2))Mi"
    else
      val="$MEM"
      mem_lim="$(($val * 2))"
    fi
    CMD+=(--requests=memory="$mem_req" --limits=memory="$mem_lim")
  fi

  "${CMD[@]}" -n $NS
fi


# 3) restart
if $RESTART; then
  echo "[SCALER] Performing rollout restart for StatefulSet '$SS_NAME'"
  kubectl rollout restart statefulset/$SS_NAME -n $NS
fi
