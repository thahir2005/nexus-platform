from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_kubernetes_deployment_health():
    with patch(
        "app.api.kubernetes.get_pod_health",
        return_value={
            "status": "healthy",
            "pod_count": 1,
            "healthy_pods": 1,
            "unhealthy_pods": 0,
            "pods": [
                {
                    "name": "test-api-pod",
                    "status": "Running",
                    "ready": True,
                    "restart_count": 0,
                    "reason": None,
                }
            ],
        },
    ):
        response = client.get(
            "/api/v1/projects/1/deployments/1/health"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["deployment_id"] == 1
    assert data["status"] == "healthy"
    assert data["pod_count"] == 1
    assert data["healthy_pods"] == 1
    assert data["unhealthy_pods"] == 0

    assert data["pods"][0]["name"] == "test-api-pod"
    assert data["pods"][0]["status"] == "Running"
    assert data["pods"][0]["ready"] is True
    assert data["pods"][0]["restart_count"] == 0
    assert data["pods"][0]["reason"] is None


def test_kubernetes_deployment_health_project_not_found():
    response = client.get(
        "/api/v1/projects/999999/deployments/1/health"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_kubernetes_deployment_health_deployment_not_found():
    response = client.get(
        "/api/v1/projects/1/deployments/999999/health"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Deployment not found"