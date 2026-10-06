from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_project():
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "api-test-project",
            "description": "API test",
            "repository_url": "https://github.com/test/api-project",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "api-test-project"
    assert data["description"] == "API test"
    assert data["owner_id"] == 1

    


def test_project_not_found():
    response = client.get("/api/v1/projects/999999")

    assert response.status_code == 404


def test_deployment_lifecycle():
    # Create a project
    project_response = client.post(
        "/api/v1/projects",
        json={
            "name": "lifecycle-test-project",
            "description": "Deployment lifecycle test",
        },
    )

    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create environment
    environment_response = client.post(
        f"/api/v1/projects/{project_id}/environments",
        json={"name": "development"},
    )

    assert environment_response.status_code == 201

    environment_id = environment_response.json()["id"]

    # Create deployment
    deployment_response = client.post(
        f"/api/v1/projects/{project_id}/environments/{environment_id}/deployments",
        json={"version": "v1.0.0"},
    )

    assert deployment_response.status_code == 201

    deployment = deployment_response.json()

    assert deployment["status"] == "pending"

    deployment_id = deployment["id"]

    # pending → running
    response = client.patch(
        f"/api/v1/projects/{project_id}/environments/"
        f"{environment_id}/deployments/{deployment_id}/status",
        json={"status": "running"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"

    # running → success
    response = client.patch(
        f"/api/v1/projects/{project_id}/environments/"
        f"{environment_id}/deployments/{deployment_id}/status",
        json={"status": "success"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # success → running must fail
    response = client.patch(
        f"/api/v1/projects/{project_id}/environments/"
        f"{environment_id}/deployments/{deployment_id}/status",
        json={"status": "running"},
    )

    assert response.status_code == 409