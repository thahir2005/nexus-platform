from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_kubernetes_deployment_status():
    with patch(
        "app.api.kubernetes.get_deployment_status",
        return_value={
            "status": "running",
            "desired_replicas": 1,
            "ready_replicas": 1,
            "available_replicas": 1,
        },
    ):
        response = client.get(
            "/api/v1/projects/1/deployments/1/status"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["deployment_id"] == 1
    assert data["status"] == "running"
    assert data["desired_replicas"] == 1
    assert data["ready_replicas"] == 1
    assert data["available_replicas"] == 1


def test_kubernetes_deployment_status_not_found():
    response = client.get(
        "/api/v1/projects/999999/deployments/1/status"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_kubernetes_deployment_not_found():
    response = client.get(
        "/api/v1/projects/1/deployments/999999/status"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Deployment not found"