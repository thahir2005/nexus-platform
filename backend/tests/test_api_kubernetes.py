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


def test_kubernetes_deployment_status():
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
            "app.api.kubernetes.get_deployment_status",
            return_value={
                "status": "running",
                "desired_replicas": 1,
                "ready_replicas": 1,
                "available_replicas": 1,
            },
        ):
            response = client.get(
                f"/api/v1/projects/{project_id}/deployments/{deployment_id}/status"
            )

        assert response.status_code == 200

        data = response.json()
        assert data["deployment_id"] == deployment_id
        assert data["status"] == "running"
        assert data["desired_replicas"] == 1
        assert data["ready_replicas"] == 1
        assert data["available_replicas"] == 1
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


def test_kubernetes_deployment_status_not_found():
    response = client.get(
        "/api/v1/projects/999999/deployments/1/status"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_kubernetes_deployment_not_found():
    project_id = create_test_project()
    try:
        response = client.get(
            f"/api/v1/projects/{project_id}/deployments/999999/status"
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
