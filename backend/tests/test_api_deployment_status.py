from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.api import deployment_status


client = TestClient(app)


def make_pipeline():
    environment = SimpleNamespace(
        id=51,
        name="development",
    )

    return SimpleNamespace(
        id=17,
        project_id=129,
        environment_id=51,
        environment=environment,
        image_name="nexus/nexus-safe-demo",
        application_name="nexus-nexus-safe-demo",
        namespace="nexus",
        build_id=66,
        security_scan_id=65,
        status="gitops_pending",
        gitops_revision="abc123",
        build_status="success",
        validation_status="valid",
        security_status="passed",
        high_count=0,
        critical_count=0,
        message="GitOps manifest published",
        created_at=datetime.now(UTC),
    )


def make_kubernetes_status(build_id=66):
    return {
        "status": "running",
        "desired_replicas": 1,
        "ready_replicas": 1,
        "available_replicas": 1,
        "deployed_build_id": build_id,
    }


def make_argo_status(
    status="available",
    sync_status="Synced",
    health_status="Healthy",
    revision="abc123",
    applied_revision="abc123",
):
    return {
        "status": status,
        "application_name": "nexus-gitops-apps",
        "sync_status": sync_status,
        "health_status": health_status,
        "revision": revision,
        "operation_phase": "Succeeded",
        "operation_message": "Sync completed",
        "applied_revision": applied_revision,
    }


def request_status(kubernetes=None, argo=None):
    pipeline = make_pipeline()

    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        id=129,
        name="NEXUS",
    )

    project = SimpleNamespace(
        id=129,
        owner_id=1,
        name="NEXUS",
    )

    project_query = MagicMock()
    project_query.filter.return_value = project_query
    project_query.first.return_value = project

    pipeline_query = MagicMock()
    pipeline_query.filter.return_value = pipeline_query
    pipeline_query.order_by.return_value = pipeline_query
    pipeline_query.first.return_value = pipeline

    db.query.side_effect = [project_query, pipeline_query]

    def override_get_db():
        yield db

    app.dependency_overrides[deployment_status.get_db] = override_get_db

    try:
        with (
            patch(
                "app.api.deployment_status.get_deployment_status",
                return_value=kubernetes or make_kubernetes_status(),
            ),
            patch(
                "app.api.deployment_status.ArgoCDService",
            ) as argo_service,
            patch(
                "app.api.deployment_status.check_application_health",
                return_value={
                    "status": "healthy",
                    "url": "https://app.example.com/health",
                    "http_status": 200,
                    "message": "Application health check succeeded",
                },
            ),

            patch(
                "app.api.deployment_status.GitOpsVerifier.verify_deployment",
                side_effect=lambda revision, **kwargs: {
                    "verified": revision == "abc123",
                    "message": (
                        "GitOps manifest matches the expected build"
                        if revision == "abc123"
                        else "Applied Git revision is missing or does not match"
                    ),
                },
            ),
        ):
            argo_service.return_value.get_status.return_value = (
                argo or make_argo_status()
            )

            response = client.get(
                "/api/v1/projects/129/deployment-status"
            )
    finally:
        app.dependency_overrides.pop(deployment_status.get_db, None)

    return response


def test_deployment_status_deployed():
    response = request_status()

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "deployed"
    assert response.json()["pipeline"]["status"] == "deployed"


def test_deployment_status_pending_when_build_does_not_match():
    response = request_status(
        kubernetes=make_kubernetes_status(build_id=65)
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "pending"


def test_deployment_status_pending_when_replicas_are_not_ready():
    kubernetes = make_kubernetes_status()
    kubernetes["ready_replicas"] = 0
    kubernetes["available_replicas"] = 0
    kubernetes["status"] = "pending"

    response = request_status(kubernetes=kubernetes)

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "pending"


def test_deployment_status_reconciling_when_revision_does_not_match():
    response = request_status(
        argo=make_argo_status(applied_revision="different-revision")
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "reconciling"


def test_deployment_status_unavailable_when_argo_is_unavailable():
    response = request_status(
        argo=make_argo_status(status="unavailable")
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "unavailable"

def test_deployment_status_pending_when_deployment_not_found():
    pipeline = make_pipeline()

    db = MagicMock()
    db.get.return_value = SimpleNamespace(id=129, name="NEXUS")

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = pipeline

    def override_get_db():
        yield db

    app.dependency_overrides[deployment_status.get_db] = override_get_db

    try:
        with (
            patch(
                "app.api.deployment_status.get_deployment_status",
                side_effect=ValueError("Kubernetes deployment not found"),
            ),
            patch(
                "app.api.deployment_status.ArgoCDService",
            ) as argo_service,
        ):
            argo_service.return_value.get_status.return_value = (
                make_argo_status()
            )

            response = client.get(
                "/api/v1/projects/129/deployment-status"
            )
    finally:
        app.dependency_overrides.pop(deployment_status.get_db, None)

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "pending"
    assert response.json()["kubernetes"]["ready_replicas"] == 0


def test_deployment_status_reconciling_when_revision_does_not_match():
    response = request_status(
        argo=make_argo_status(
            applied_revision="different-revision"
        )
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "reconciling"

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "reconciling"

def test_deployment_status_pending_when_application_health_fails():
    pipeline = make_pipeline()

    db = MagicMock()
    db.get.return_value = SimpleNamespace(id=129, name="NEXUS")

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = pipeline

    def override_get_db():
        yield db

    app.dependency_overrides[deployment_status.get_db] = override_get_db

    try:
        with (
            patch(
                "app.api.deployment_status.get_deployment_status",
                return_value=make_kubernetes_status(),
            ),
            patch(
                "app.api.deployment_status.ArgoCDService",
            ) as argo_service,
            patch(
                "app.api.deployment_status.check_application_health",
                return_value={
                    "status": "unhealthy",
                    "url": "https://app.example.com/health",
                    "http_status": 500,
                    "message": "Application health check failed",
                },
            ),
        ):
            argo_service.return_value.get_status.return_value = (
                make_argo_status()
            )

            response = client.get(
                "/api/v1/projects/129/deployment-status"
            )
    finally:
        app.dependency_overrides.pop(deployment_status.get_db, None)

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "pending"
    assert response.json()["application_health"]["status"] == "unhealthy"


def test_deployment_status_deployed_when_applied_revision_matches():
    response = request_status(
        argo=make_argo_status(
            revision="newer-tracked-revision",
            applied_revision="abc123",
        )
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "deployed"


def test_deployment_status_reconciling_when_applied_revision_missing():
    response = request_status(
        argo=make_argo_status(applied_revision=None)
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "reconciling"


def test_deployment_status_reconciling_when_out_of_sync():
    response = request_status(
        argo=make_argo_status(sync_status="OutOfSync")
    )

    assert response.status_code == 200
    assert response.json()["deployment_state"] == "reconciling"
