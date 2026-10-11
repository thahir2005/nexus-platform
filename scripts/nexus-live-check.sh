#!/bin/bash
set -euo pipefail

NAMESPACE=nexus
DEPLOYMENT=nexus-demo-api
PORT=18002

echo "=== NEXUS Live Deployment ==="
kubectl rollout status deployment/"$DEPLOYMENT" \
  -n "$NAMESPACE" --timeout=60s

echo
echo "=== Deployment Image ==="
kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

echo
echo "=== Pod Status ==="
kubectl get pods -n "$NAMESPACE"

echo
echo "=== GitOps Verifier ==="
kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT" -- \
  python -c "from app.services.gitops_verifier import GitOpsVerifier; print('GitOps verifier available')"

echo
echo "=== Starting Temporary Port Forward ==="
LOG_FILE="$(mktemp)"
kubectl port-forward -n "$NAMESPACE" deployment/"$DEPLOYMENT" \
  "$PORT:8000" >"$LOG_FILE" 2>&1 &
PF_PID=$!

cleanup() {
  kill "$PF_PID" 2>/dev/null || true
  wait "$PF_PID" 2>/dev/null || true
  rm -f "$LOG_FILE"
}
trap cleanup EXIT

READY=0
for i in $(seq 1 20); do
  if curl --noproxy '*' -fsS \
    "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "$READY" -ne 1 ]]; then
  echo "FAIL: Backend health endpoint did not respond."
  cat "$LOG_FILE"
  exit 1
fi

echo
echo "=== API Health ==="
curl --noproxy '*' -fsS "http://127.0.0.1:$PORT/health"
echo

echo
echo "=== Root Endpoint ==="
curl --noproxy '*' -fsS "http://127.0.0.1:$PORT/"
echo

echo
echo "PASS: NEXUS live checks completed."
