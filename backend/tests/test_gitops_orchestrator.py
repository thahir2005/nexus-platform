from unittest.mock import Mock, patch

from app.services.deployment_orchestrator import run_deployment_pipeline


def test_gitops_mode_publishes_after_successful_build(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.deployment_orchestrator.settings.gitops_enabled",
        True,
    )

    db = Mock()

    project = Mock(id=1, name="Student API")
    environment = Mock(id=1, name="development")

    db.get.side_effect = [project, environment]

    build_result = Mock(
        status="success",
        build_id=101,
        security_scan_id=201,
        build_status="success",
        validation_status="valid",
        security_status="passed",
        high_count=0,
        critical_count=0,
    )

    gitops_result = Mock(
        status="published",
        revision="abc123",
        message="GitOps manifest committed and pushed successfully",
    )

    with patch(
        "app.services.deployment_orchestrator.prepare_build_context"
    ), patch(
        "app.services.deployment_orchestrator.run_build_pipeline",
        return_value=build_result,
    ), patch(
        "app.services.deployment_orchestrator.GitOpsPublisher.publish",
        return_value=gitops_result,
    ) as publish:
        result = run_deployment_pipeline(
            db=db,
            project_id=1,
            environment_id=1,
            repository_path="/tmp/project",
            image_name="nexus/student-api",
            application_name="nexus-student-api",
        )

    publish.assert_called_once()
    assert result.status == "gitops_pending"
    assert result.deployment_id is None
    assert result.build_id == 101


def test_gitops_mode_does_not_publish_when_security_blocks(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.deployment_orchestrator.settings.gitops_enabled",
        True,
    )

    db = Mock()

    build_result = Mock(
        status="blocked",
        build_id=102,
        security_scan_id=202,
        build_status="success",
        validation_status="valid",
        security_status="blocked",
        high_count=12,
        critical_count=0,
        message="Security scan blocked deployment",
    )

    with patch(
        "app.services.deployment_orchestrator.prepare_build_context"
    ), patch(
        "app.services.deployment_orchestrator.run_build_pipeline",
        return_value=build_result,
    ), patch(
        "app.services.deployment_orchestrator.GitOpsPublisher.publish"
    ) as publish:
        result = run_deployment_pipeline(
            db=db,
            project_id=1,
            environment_id=1,
            repository_path="/tmp/project",
            image_name="nexus/student-api",
            application_name="nexus-student-api",
        )

    publish.assert_not_called()
    assert result.status == "blocked"
    assert result.deployment_id is None
