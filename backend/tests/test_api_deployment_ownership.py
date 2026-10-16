from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.auth import get_current_user, require_request_access
from app.db.session import SessionLocal
from app.main import app
from app.models.deployment import Deployment
from app.models.environment import Environment
from app.models.project import Project
from app.models.user import User

client = TestClient(app)


def _create_foreign_deployment():
    db = SessionLocal()
    suffix = uuid4().hex

    try:
        owner = User(
            username=f"deploy-owner-{suffix[:12]}",
            email=f"deploy-owner-{suffix}@example.invalid",
        )
        db.add(owner)
        db.flush()

        project = Project(
            name=f"deploy-private-{suffix}",
            description="Deployment ownership regression test",
            owner_id=owner.id,
            repository_url="https://github.com/example/project",
        )
        db.add(project)
        db.flush()

        environment = Environment(
            name="development",
            project_id=project.id,
        )
        db.add(environment)
        db.flush()

        deployment = Deployment(
            version="ownership-test",
            status="pending",
            environment_id=environment.id,
        )
        db.add(deployment)
        db.commit()

        return project.id, environment.id, deployment.id, owner.id
    finally:
        db.close()


def _current_test_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == "nexus-test-auth@example.invalid"
        ).first()
        assert user is not None, "Expected authenticated test user to exist"
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            clerk_user_id=user.clerk_user_id,
        )
    finally:
        db.close()


def _delete_records(project_id, environment_id, deployment_id, owner_id):
    db = SessionLocal()
    try:
        db.query(Deployment).filter(
            Deployment.id == deployment_id
        ).delete(synchronize_session=False)
        db.query(Environment).filter(
            Environment.id == environment_id
        ).delete(synchronize_session=False)
        db.query(Project).filter(
            Project.id == project_id
        ).delete(synchronize_session=False)
        db.query(User).filter(User.id == owner_id).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def _run_as_different_user():
    saved = {
        get_current_user: app.dependency_overrides.pop(get_current_user, None),
        require_request_access: app.dependency_overrides.pop(
            require_request_access, None
        ),
    }
    app.dependency_overrides[get_current_user] = _current_test_user
    return saved


def _restore_overrides(saved):
    for dependency, override in saved.items():
        app.dependency_overrides.pop(dependency, None)
        if override is not None:
            app.dependency_overrides[dependency] = override


def test_cannot_list_another_users_deployments():
    project_id, environment_id, deployment_id, owner_id = (
        _create_foreign_deployment()
    )
    saved = _run_as_different_user()

    try:
        response = client.get(
            f"/api/v1/projects/{project_id}/environments/"
            f"{environment_id}/deployments"
        )
        assert response.status_code == 404
    finally:
        _restore_overrides(saved)
        _delete_records(project_id, environment_id, deployment_id, owner_id)


def test_cannot_read_another_users_deployment():
    project_id, environment_id, deployment_id, owner_id = (
        _create_foreign_deployment()
    )
    saved = _run_as_different_user()

    try:
        response = client.get(
            f"/api/v1/projects/{project_id}/environments/"
            f"{environment_id}/deployments/{deployment_id}"
        )
        assert response.status_code == 404
    finally:
        _restore_overrides(saved)
        _delete_records(project_id, environment_id, deployment_id, owner_id)


def test_cannot_update_another_users_deployment():
    project_id, environment_id, deployment_id, owner_id = (
        _create_foreign_deployment()
    )
    saved = _run_as_different_user()

    try:
        response = client.patch(
            f"/api/v1/projects/{project_id}/environments/"
            f"{environment_id}/deployments/{deployment_id}/status",
            json={"status": "running"},
        )
        assert response.status_code == 404
    finally:
        _restore_overrides(saved)
        _delete_records(project_id, environment_id, deployment_id, owner_id)
