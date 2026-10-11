from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.project import Project


client = TestClient(app)


def create_test_project():
    response = client.post(
        "/api/v1/projects",
        json={"name": f"rollback-test-{uuid4().hex}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def delete_test_project(project_id):
    db = SessionLocal()
    try:
        db.query(Project).filter(Project.id == project_id).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def test_kubernetes_deployment_rollback():
    project_id = create_test_project()
    rollback_result = SimpleNamespace(
        status="rolled_back",
        project_id=project_id,
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

    try:
        with patch(
            "app.api.kubernetes.rollback_deployment",
            return_value=rollback_result,
        ):
            response = client.post(
                f"/api/v1/projects/{project_id}/deployments/5/rollback"
            )
    finally:
        delete_test_project(project_id)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "rolled_back"
    assert data["project_id"] == project_id
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
    project_id = create_test_project()
    try:
        with patch(
            "app.api.kubernetes.rollback_deployment",
            side_effect=ValueError(
                "No previous successful deployment is available for rollback"
            ),
        ):
            response = client.post(
                f"/api/v1/projects/{project_id}/deployments/5/rollback"
            )
    finally:
        delete_test_project(project_id)

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "No previous successful deployment is available for rollback"
    )
