from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.auth import get_current_user, require_request_access
from app.db.session import SessionLocal
from app.main import app
from app.models.environment import Environment
from app.models.project import Project
from app.models.user import User

client = TestClient(app)


def _create_foreign_project():
    """Create a project owned by a different user for authorization tests."""
    suffix = uuid4().hex
    db = SessionLocal()

    try:
        user = User(
            username=f"auth-owner-{suffix[:12]}",
            email=f"auth-owner-{suffix}@example.invalid",
        )
        db.add(user)
        db.flush()

        project = Project(
            name=f"private-project-{suffix}",
            description="Ownership isolation test",
            owner_id=user.id,
            repository_url="https://github.com/example/project",
        )
        db.add(project)
        db.flush()

        environment = Environment(
            name="development",
            project_id=project.id,
        )
        db.add(environment)
        db.commit()

        return project.id, environment.id, user.id
    finally:
        db.close()


def _delete_foreign_project(project_id, environment_id, user_id):
    db = SessionLocal()
    try:
        db.query(Environment).filter(
            Environment.id == environment_id
        ).delete(synchronize_session=False)

        db.query(Project).filter(Project.id == project_id).delete(
            synchronize_session=False
        )

        db.query(User).filter(User.id == user_id).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def _remove_auth_overrides():
    """Temporarily restore real authentication and ownership dependencies."""
    saved = {}

    for dependency in (get_current_user, require_request_access):
        saved[dependency] = app.dependency_overrides.pop(dependency, None)

    return saved


def _restore_auth_overrides(saved):
    for dependency, override in saved.items():
        if override is not None:
            app.dependency_overrides[dependency] = override


def test_projects_require_authentication():
    saved = _remove_auth_overrides()
    try:
        response = client.get("/api/v1/projects")
        assert response.status_code == 401
    finally:
        _restore_auth_overrides(saved)


def test_user_cannot_read_another_users_project():
    project_id, environment_id, user_id = _create_foreign_project()
    saved = _remove_auth_overrides()

    try:
        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 401
    finally:
        _restore_auth_overrides(saved)
        _delete_foreign_project(project_id, environment_id, user_id)


def test_authenticated_user_cannot_read_another_users_project():
    project_id, environment_id, user_id = _create_foreign_project()
    saved = _remove_auth_overrides()

    try:
        # Simulate a valid session for the normal test user, but retain
        # the real project ownership dependency.
        from app.models.user import User as UserModel

        db = SessionLocal()
        try:
            current_user = db.scalar(
                select(UserModel).where(
                    UserModel.email == "nexus-test-auth@example.invalid"
                )
            )
            assert current_user is not None
            current_user_id = current_user.id
        finally:
            db.close()

        app.dependency_overrides[get_current_user] = lambda: _get_user(
            current_user_id
        )

        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 404
    finally:
        _restore_auth_overrides(saved)
        _delete_foreign_project(project_id, environment_id, user_id)


def _get_user(user_id):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        assert user is not None
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            clerk_user_id=user.clerk_user_id,
        )
    finally:
        db.close()


def test_user_cannot_access_another_users_deployment_history():
    project_id, environment_id, user_id = _create_foreign_project()
    saved = _remove_auth_overrides()

    try:
        current_user_id = _get_test_user_id()
        app.dependency_overrides[get_current_user] = lambda: _get_user(
            current_user_id
        )

        response = client.get(
            f"/api/v1/projects/{project_id}/deployment-history"
        )
        assert response.status_code == 404
    finally:
        _restore_auth_overrides(saved)
        _delete_foreign_project(project_id, environment_id, user_id)


def test_user_cannot_start_deployment_pipeline_for_another_users_project():
    project_id, environment_id, user_id = _create_foreign_project()
    saved = _remove_auth_overrides()

    try:
        current_user_id = _get_test_user_id()
        app.dependency_overrides[get_current_user] = lambda: _get_user(
            current_user_id
        )

        with patch(
            "app.api.deployment_pipeline.prepare_repository_workspace"
        ) as prepare_workspace:
            response = client.post(
                f"/api/v1/projects/{project_id}/deploy-pipeline",
                json={"environment_id": environment_id},
            )

        assert response.status_code == 404
        prepare_workspace.assert_not_called()
    finally:
        _restore_auth_overrides(saved)
        _delete_foreign_project(project_id, environment_id, user_id)


def test_user_cannot_deploy_another_users_project_to_kubernetes():
    project_id, environment_id, user_id = _create_foreign_project()
    saved = _remove_auth_overrides()

    try:
        current_user_id = _get_test_user_id()
        app.dependency_overrides[get_current_user] = lambda: _get_user(
            current_user_id
        )

        with patch("app.api.kubernetes.deploy_application") as deploy:
            response = client.post(
                f"/api/v1/projects/{project_id}/deploy",
                json={
                    "image_name": f"nexus/project-{project_id}",
                    "application_name": f"nexus-project-{project_id}",
                    "namespace": "nexus",
                    "replicas": 1,
                },
            )

        assert response.status_code == 404
        deploy.assert_not_called()
    finally:
        _restore_auth_overrides(saved)
        _delete_foreign_project(project_id, environment_id, user_id)


def _get_test_user_id():
    db = SessionLocal()
    try:
        user = db.scalar(
            select(User).where(
                User.email == "nexus-test-auth@example.invalid"
            )
        )
        assert user is not None
        return user.id
    finally:
        db.close()

def test_user_cannot_rollback_another_users_deployment():
    from app.models.kubernetes_deployment import KubernetesDeployment

    project_id, environment_id, user_id = _create_foreign_project()
    db = SessionLocal()
    deployment_id = None

    try:
        deployment = KubernetesDeployment(
            project_id=project_id,
            environment_id=environment_id,
            image_name="nexus/test-private",
            application_name="nexus-test-private",
            namespace="nexus",
            replicas=1,
            status="deployed",
        )
        db.add(deployment)
        db.commit()
        deployment_id = deployment.id
    finally:
        db.close()

    saved = _remove_auth_overrides()

    try:
        current_user_id = _get_test_user_id()
        app.dependency_overrides[get_current_user] = lambda: _get_user(
            current_user_id
        )

        with patch("app.api.kubernetes.rollback_deployment") as rollback:
            response = client.post(
                f"/api/v1/projects/{project_id}/deployments/"
                f"{deployment_id}/rollback"
            )

        assert response.status_code == 404
        rollback.assert_not_called()
    finally:
        _restore_auth_overrides(saved)

        cleanup_db = SessionLocal()
        try:
            if deployment_id is not None:
                cleanup_db.query(KubernetesDeployment).filter(
                    KubernetesDeployment.id == deployment_id
                ).delete(synchronize_session=False)
                cleanup_db.commit()
        finally:
            cleanup_db.close()

        _delete_foreign_project(project_id, environment_id, user_id)
