#!/bin/bash

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

section() {
  printf '\n\n========================================\n'
  printf ' %s\n' "$1"
  printf '========================================\n'
}

run_check() {
  local description="$1"
  shift

  printf '\n▶ %s\n' "$description"

  if "$@"; then
    printf '✓ PASS: %s\n' "$description"
  else
    printf '✗ FAIL: %s\n' "$description"
    return 1
  fi
}

section "NEXUS ENVIRONMENT"

run_check "Docker is available" docker info --format '{{.ServerVersion}}' || exit 1
run_check "Minikube is running" minikube status || exit 1

section "KUBERNETES"

run_check "Kubernetes nodes are available" kubectl get nodes || exit 1
run_check "NEXUS deployment status" kubectl get deployments -n nexus || exit 1

section "DATABASE"

run_check "PostgreSQL is healthy" docker exec nexus-postgres pg_isready || exit 1
run_check "NEXUS database schema is available" \
  docker exec nexus-postgres psql -U nexus -d nexus -c \
  "SELECT version_num FROM alembic_version;" || exit 1

section "BACKEND IMAGE"

run_check "Backend image exists locally" \
  docker image inspect nexus/devops-production-platform:v2 \
  --format '{{.Id}}' || exit 1

run_check "GitOps verifier imports" \
  docker run --rm \
  -e DATABASE_URL='postgresql+psycopg://test:test@localhost:5432/test' \
  --entrypoint python \
  nexus/devops-production-platform:v2 \
  -c "from app.services.gitops_verifier import GitOpsVerifier; print('GitOps verifier import successful')" || exit 1

section "GIT STATUS"
git status --short

section "CHECKS COMPLETE"
echo "Environment checks completed."
echo "No Kubernetes deployments or database schemas were changed."
