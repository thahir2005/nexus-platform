from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

from app.db.session import SessionLocal
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.project import Project


client = TestClient(app)


def create_test_project():
    response = client.post(
        "/api/v1/projects",
        json={"name": f"kubernetes-test-{uuid4().hex}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_kubernetes_deployment_health():
    project_id = create_test_project()
    db = SessionLocal()
    deployment = KubernetesDeployment(
        project_id=project_id,
        image_name="nexus/test-api:latest",
        application_name="test-api",
        namespace="nexus",
        replicas=1,
        status="running",
    )

    try:
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        deployment_id = deployment.id
    finally:
        db.close()

    try:
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
                f"/api/v1/projects/{project_id}/deployments/{deployment_id}/health"
            )

        assert response.status_code == 200

        data = response.json()
        assert data["deployment_id"] == deployment_id
        assert data["status"] == "healthy"
        assert data["pod_count"] == 1
        assert data["healthy_pods"] == 1
        assert data["unhealthy_pods"] == 0
        assert data["pods"][0]["name"] == "test-api-pod"
        assert data["pods"][0]["status"] == "Running"
        assert data["pods"][0]["ready"] is True
        assert data["pods"][0]["restart_count"] == 0
        assert data["pods"][0]["reason"] is None
    finally:
        db = SessionLocal()
        try:
            db.query(KubernetesDeployment).filter(
                KubernetesDeployment.project_id == project_id
            ).delete(synchronize_session=False)
            db.query(Project).filter(Project.id == project_id).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()


def test_kubernetes_deployment_health_project_not_found():
    response = client.get(
        "/api/v1/projects/999999/deployments/1/health"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_kubernetes_deployment_health_deployment_not_found():
    project_id = create_test_project()
    try:
        response = client.get(
            f"/api/v1/projects/{project_id}/deployments/999999/health"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Deployment not found"
    finally:
        db = SessionLocal()
        try:
            db.query(KubernetesDeployment).filter(
                KubernetesDeployment.project_id == project_id
            ).delete(synchronize_session=False)
            db.query(Project).filter(Project.id == project_id).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()
