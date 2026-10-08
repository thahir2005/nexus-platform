from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import deployment_rollback


def test_rollback_uses_previous_successful_deployment(monkeypatch):
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
