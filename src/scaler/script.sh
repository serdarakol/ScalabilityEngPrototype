#!/usr/bin/env bash
set -euo pipefail

# Configuration
NS=${NAMESPACE:-default}
SS_NAME=${STATEFULSET_NAME:-species}

# Default target values for demonstration
TARGET_REPLICAS=${REPLICAS:-4}
BASE_CPU_REQUEST=${BASE_CPU_REQUEST:-200m}
BASE_MEM_REQUEST=${BASE_MEM_REQUEST:-256Mi}
BASE_CPU_LIMIT=${BASE_CPU_LIMIT:-500m}
BASE_MEM_LIMIT=${BASE_MEM_LIMIT:-512Mi}

usage() {
  echo "Usage: $0 [--replicas N] [--double-resources] [--restart]"
  echo "  --replicas N         Scale to N replicas (default: $TARGET_REPLICAS)"
  echo "  --double-resources    Double CPU and memory from base values"
  echo "  --restart            Rollout restart the StatefulSet after changes"
  exit 1
}

# Flags
DOUBLERES=false
RESTART=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --replicas)
      TARGET_REPLICAS=$2; shift 2;;
    --double-resources)
      DOUBLERES=true; shift;;
    --restart)
      RESTART=true; shift;;
    *) usage;;
  esac
done

# 1) Horizontal scaling
echo "[SCALER] Scaling StatefulSet '$SS_NAME' in namespace '$NS' to $TARGET_REPLICAS replicas"
kubectl scale statefulset/$SS_NAME --replicas=$TARGET_REPLICAS -n $NS

# 2) Vertical scaling
if $DOUBLERES; then
  echo "[SCALER] Doubling resources from base values"
  # CPU request
  cpu_req_val=${BASE_CPU_REQUEST%m}
  cpu_req_doubled=$((cpu_req_val * 2))
  new_cpu_request="${cpu_req_doubled}m"
  # Memory request
  mem_req_val=${BASE_MEM_REQUEST%Mi}
  mem_req_doubled=$((mem_req_val * 2))
  new_mem_request="${mem_req_doubled}Mi"
  # CPU limit
  cpu_lim_val=${BASE_CPU_LIMIT%m}
  cpu_lim_doubled=$((cpu_lim_val * 2))
  new_cpu_limit="${cpu_lim_doubled}m"
  # Memory limit
  mem_lim_val=${BASE_MEM_LIMIT%Mi}
  mem_lim_doubled=$((mem_lim_val * 2))
  new_mem_limit="${mem_lim_doubled}Mi"

  echo "[SCALER] Setting requests: cpu=$new_cpu_request, memory=$new_mem_request"
  echo "[SCALER] Setting limits:   cpu=$new_cpu_limit, memory=$new_mem_limit"

  kubectl set resources statefulset/$SS_NAME \
    --containers=species-service \
    --requests=cpu=$new_cpu_request,memory=$new_mem_request \
    --limits=cpu=$new_cpu_limit,memory=$new_mem_limit -n $NS
fi

# 3) restart
  echo "[SCALER] Performing rollout restart for StatefulSet '$SS_NAME'"
  kubectl rollout restart statefulset/$SS_NAME -n $NS
fi
