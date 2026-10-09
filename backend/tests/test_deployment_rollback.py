from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import deployment_rollback


def test_rollback_uses_previous_successful_deployment(monkeypatch):
    monkeypatch.setattr(deployment_rollback.settings, 'gitops_enabled', False)
    db = Mock()

    current = SimpleNamespace(
        id=5,
        project_id=1,
        environment_id=1,
        image_name="nexus/current",
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )

    target = SimpleNamespace(
        id=3,
        image_name="nexus/previous",
    )

    previous_run = SimpleNamespace(
        deployment=target,
        build_id=65,
    )

    db.get.return_value = current

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = previous_run

    deployment_result = SimpleNamespace(
        status="deployed",
        deployment_name="nexus-test-api",
        service_name="nexus-test-api",
        namespace="nexus",
    )

    monkeypatch.setattr(
        deployment_rollback,
        "deploy_application",
        Mock(return_value=deployment_result),
    )

    result = deployment_rollback.rollback_deployment(
        db=db,
        project_id=1,
        deployment_id=5,
    )

    assert result.status == "rolled_back"
    assert result.project_id == 1
    assert result.environment_id == 1
    assert result.rollback_of_id == 5
    assert result.image_name == "nexus/previous"
    assert result.deployment_name == "nexus-test-api"

    deployment_rollback.deploy_application.assert_called_once_with(
        image_name="nexus/previous",
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_rollback_rejects_deployment_from_another_project():
    db = Mock()

    current = SimpleNamespace(
        id=5,
        project_id=2,
        environment_id=1,
    )

    db.get.return_value = current

    with pytest.raises(ValueError, match="Deployment not found"):
        deployment_rollback.rollback_deployment(
            db=db,
            project_id=1,
            deployment_id=5,
        )


def test_rollback_rejects_when_no_previous_deployment_exists():
    db = Mock()

    current = SimpleNamespace(
        id=5,
        project_id=1,
        environment_id=1,
        image_name="nexus/current",
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )

    db.get.return_value = current

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None

    with pytest.raises(
        ValueError,
        match="No previous successful deployment is available for rollback",
    ):
        deployment_rollback.rollback_deployment(
            db=db,
            project_id=1,
            deployment_id=5,
        )


def test_rollback_does_not_create_record_when_deployment_fails(monkeypatch):
    monkeypatch.setattr(deployment_rollback.settings, 'gitops_enabled', False)
    db = Mock()

    current = SimpleNamespace(
        id=5,
        project_id=1,
        environment_id=1,
        image_name="nexus/current",
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )

    target = SimpleNamespace(
        id=3,
        image_name="nexus/previous",
    )

    previous_run = SimpleNamespace(
        deployment=target,
        build_id=65,
    )

    db.get.return_value = current

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = previous_run

    monkeypatch.setattr(
        deployment_rollback,
        "deploy_application",
        Mock(side_effect=ValueError("Kubernetes deployment failed")),
    )

    with pytest.raises(
        ValueError,
        match="Kubernetes deployment failed",
    ):
        deployment_rollback.rollback_deployment(
            db=db,
            project_id=1,
            deployment_id=5,
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_gitops_rollback_publishes_previous_image_without_direct_deploy(
    monkeypatch,
):
    monkeypatch.setattr(
        deployment_rollback.settings,
        "gitops_enabled",
        True,
    )

    db = Mock()

    current = SimpleNamespace(
        id=6,
        project_id=1,
        environment_id=2,
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )
    target = SimpleNamespace(id=3, image_name="nexus/previous")
    previous_run = SimpleNamespace(deployment=target, build_id=65)
    project = SimpleNamespace(name="Student API")
    environment = SimpleNamespace(name="development")

    db.get.side_effect = [current, project, environment]

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = previous_run

    publish_result = SimpleNamespace(
        status="published",
        revision="abc123",
        manifest_path="infrastructure/gitops/apps/student-api/development/application.yaml",
        message="GitOps manifest committed and pushed successfully",
    )

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.services.deployment_rollback.load_local_image_into_minikube"
        ) as load_image,
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            deployment_rollback.GitOpsPublisher,
            "publish",
            return_value=publish_result,
        ) as publish,
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            deployment_rollback,
            "deploy_application",
        ) as direct_deploy,
    ):
        result = deployment_rollback.rollback_deployment(
            db=db,
            project_id=1,
            deployment_id=6,
        )

    load_image.assert_called_once_with("nexus/previous")
    publish.assert_called_once_with(
        project_name="Student API",
        environment_name="development",
        application_name="nexus-test-api",
        image_name="nexus/previous",
        namespace="nexus",
        replicas=1,
        build_id=65,
    )
    direct_deploy.assert_not_called()

    assert result.status == "gitops_pending"
    assert result.image_name == "nexus/previous"
    assert db.add.call_args.args[0].status == "gitops_pending"
    db.commit.assert_called_once()


def test_gitops_rollback_does_not_record_failed_publication(monkeypatch):
    monkeypatch.setattr(
        deployment_rollback.settings,
        "gitops_enabled",
        True,
    )

    db = Mock()

    current = SimpleNamespace(
        id=6,
        project_id=1,
        environment_id=2,
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )
    target = SimpleNamespace(id=3, image_name="nexus/previous")
    previous_run = SimpleNamespace(deployment=target, build_id=65)

    db.get.side_effect = [
        current,
        SimpleNamespace(name="Student API"),
        SimpleNamespace(name="development"),
    ]

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = previous_run

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.services.deployment_rollback.load_local_image_into_minikube"
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            deployment_rollback.GitOpsPublisher,
            "publish",
            return_value=SimpleNamespace(
                status="failed",
                revision=None,
                manifest_path="",
                message="Push failed",
            ),
        ),
    ):
        with pytest.raises(ValueError, match="GitOps rollback publication failed"):
            deployment_rollback.rollback_deployment(
                db=db,
                project_id=1,
                deployment_id=6,
            )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_gitops_rollback_handles_unchanged_manifest(monkeypatch):
    monkeypatch.setattr(
        deployment_rollback.settings,
        "gitops_enabled",
        True,
    )

    db = Mock()
    current = SimpleNamespace(
        id=6,
        project_id=1,
        environment_id=2,
        application_name="nexus-test-api",
        namespace="nexus",
        replicas=1,
    )
    target = SimpleNamespace(id=3, image_name="nexus/previous")
    previous_run = SimpleNamespace(deployment=target, build_id=65)

    db.get.side_effect = [
        current,
        SimpleNamespace(name="Student API"),
        SimpleNamespace(name="development"),
    ]

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = previous_run

    unchanged_result = SimpleNamespace(
        status="unchanged",
        revision=None,
        manifest_path="infrastructure/gitops/apps/student-api/development/application.yaml",
        message="GitOps manifest already matches desired state",
    )

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.services.deployment_rollback.load_local_image_into_minikube"
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            deployment_rollback.GitOpsPublisher,
            "publish",
            return_value=unchanged_result,
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            deployment_rollback,
            "deploy_application",
        ) as direct_deploy,
    ):
        result = deployment_rollback.rollback_deployment(
            db=db,
            project_id=1,
            deployment_id=6,
        )

    direct_deploy.assert_not_called()
    assert result.status == "gitops_pending"
    assert "already matches" in result.message
    assert db.add.call_args.args[0].status == "gitops_pending"
    db.commit.assert_called_once()
