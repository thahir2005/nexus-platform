from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_kubernetes_deployment_rollback():
    rollback_result = SimpleNamespace(
        status="rolled_back",
        project_id=1,
        environment_id=1,
        deployment_id=6,
        rollback_of_id=5,
        image_name="nexus/previous",
        deployment_name="nexus-test-api",
        service_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
        message="Rolled back deployment 5 to previous deployment 3; 1/1 replicas ready",
    )

    with patch(
        "app.api.kubernetes.rollback_deployment",
        return_value=rollback_result,
    ):
        response = client.post(
            "/api/v1/projects/1/deployments/5/rollback"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "rolled_back"
    assert data["project_id"] == 1
    assert data["environment_id"] == 1
    assert data["deployment_id"] == 6
    assert data["rollback_of_id"] == 5
    assert data["image_name"] == "nexus/previous"
    assert data["deployment_name"] == "nexus-test-api"
    assert data["replicas"] == 1


def test_kubernetes_deployment_rollback_not_found():
    response = client.post(
        "/api/v1/projects/999999/deployments/5/rollback"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_kubernetes_deployment_rollback_error():
    with patch(
        "app.api.kubernetes.rollback_deployment",
        side_effect=ValueError(
            "No previous successful deployment is available for rollback"
        ),
    ):
        response = client.post(
            "/api/v1/projects/1/deployments/5/rollback"
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "No previous successful deployment is available for rollback"
    )
