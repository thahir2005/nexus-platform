from types import SimpleNamespace
from unittest.mock import Mock

from app.services import deployment_orchestrator
from app.models.deployment_pipeline_run import DeploymentPipelineRun


def test_orchestrator_blocks_deployment_when_build_pipeline_fails(monkeypatch):
    db = Mock()

    build_result = SimpleNamespace(
        status="failed",
        image_name="nexus/test-app",
        build_status="success",
        validation_status="valid",
        security_status="blocked",
        architecture="arm64",
        os="linux",
        high_count=2,
        critical_count=0,
        message="Security gate blocked",
        build_id=10,
        security_scan_id=20,
    )

    monkeypatch.setattr(
        deployment_orchestrator,
        "run_build_pipeline",
        lambda **kwargs: build_result,
    )

    monkeypatch.setattr(
        deployment_orchestrator,
        "prepare_build_context",
        lambda *args, **kwargs: "/tmp/test-app",
    )

    deploy_mock = Mock()
    monkeypatch.setattr(
        deployment_orchestrator,
        "deploy_application",
        deploy_mock,
    )

    result = deployment_orchestrator.run_deployment_pipeline(
        db=db,
        project_id=1,
        environment_id=1,
        repository_path="/tmp/test-app",
        image_name="nexus/test-app",
        application_name="test-app",
    )

    assert result.status == "blocked"
    assert result.build_id == 10
    assert result.security_scan_id == 20
    assert result.deployment_id is None
    assert result.security_status == "blocked"
    deploy_mock.assert_not_called()


def test_orchestrator_deploys_after_successful_build(monkeypatch):
    db = Mock()

    build_result = SimpleNamespace(
        status="success",
        image_name="nexus/test-app",
        build_status="success",
        validation_status="valid",
        security_status="passed",
        architecture="arm64",
        os="linux",
        high_count=0,
        critical_count=0,
        message="Build, validation, and security scan completed successfully",
        build_id=11,
        security_scan_id=21,
    )

    deployment_result = SimpleNamespace(
        status="deployed",
        deployment_name="test-app",
        service_name="test-app",
        namespace="nexus",
        message="Application deployed successfully",
    )

    monkeypatch.setattr(
        deployment_orchestrator,
        "run_build_pipeline",
        lambda **kwargs: build_result,
    )

    monkeypatch.setattr(
        deployment_orchestrator,
        "prepare_build_context",
        lambda *args, **kwargs: "/tmp/test-app",
    )

    monkeypatch.setattr(
        deployment_orchestrator,
        "deploy_application",
        lambda **kwargs: deployment_result,
    )

    db.refresh = Mock()

    result = deployment_orchestrator.run_deployment_pipeline(
        db=db,
        project_id=1,
        environment_id=1,
        repository_path="/tmp/test-app",
        image_name="nexus/test-app",
        application_name="test-app",
    )

    assert result.status == "deployed"
    assert result.build_id == 11
    assert result.security_scan_id == 21
    assert result.deployment_name == "test-app"
    assert result.service_name == "test-app"
    assert result.namespace == "nexus"

    assert db.add.call_count == 2
    added_objects = [
        call.args[0]
        for call in db.add.call_args_list
    ]    
    assert any(
        isinstance(obj, DeploymentPipelineRun)
        for obj in added_objects

    )
    assert db.commit.call_count == 2
    db.refresh.assert_called_once()
