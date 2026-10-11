#!/bin/bash
set -euo pipefail

NAMESPACE=nexus
POD=nexus-backend-db-check

cleanup() {
  kubectl delete pod "$POD" -n "$NAMESPACE" \
    --ignore-not-found --wait=true >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

kubectl run "$POD" \
  -n "$NAMESPACE" \
  --image=nexus/devops-production-platform:v2 \
  --image-pull-policy=IfNotPresent \
  --restart=Never \
  --overrides='{
    "apiVersion":"v1",
    "spec":{
      "containers":[{
        "name":"check",
        "image":"nexus/devops-production-platform:v2",
        "imagePullPolicy":"IfNotPresent",
        "envFrom":[{"secretRef":{"name":"nexus-backend-config"}}],
        "command":["python","-c",
          "from sqlalchemy import text; from app.db.session import engine; c=engine.connect(); print(c.execute(text(\"SELECT current_database(), current_user\")).one()); c.close()"]
      }],
      "restartPolicy":"Never"
    }
  }'

echo "Waiting for database test..."
for i in $(seq 1 30); do
  phase=$(kubectl get pod "$POD" -n "$NAMESPACE" \
    -o jsonpath='{.status.phase}' 2>/dev/null || true)

  if [[ "$phase" == "Succeeded" ]]; then
    kubectl logs "$POD" -n "$NAMESPACE"
    echo "PASS: New backend connected to PostgreSQL."
    exit 0
  fi

  if [[ "$phase" == "Failed" ]]; then
    kubectl logs "$POD" -n "$NAMESPACE" || true
    echo "FAIL: Database connection test failed."
    exit 1
  fi

  sleep 2
done

kubectl describe pod "$POD" -n "$NAMESPACE"
echo "FAIL: Timed out waiting for database test."
exit 1
