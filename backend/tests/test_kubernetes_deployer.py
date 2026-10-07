from unittest.mock import MagicMock, patch

from kubernetes.client.exceptions import ApiException

from app.services.kubernetes_deployer import deploy_application

from app.services.kubernetes_deployer import (
    deploy_application,
    get_deployment_status,
)


def test_deploy_creates_resources():
    apps_api = MagicMock()
    core_api = MagicMock()

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.AppsV1Api",
            return_value=apps_api,
        ),
        patch(
            "app.services.kubernetes_deployer.client.CoreV1Api",
            return_value=core_api,
        ),
    ):
        result = deploy_application(
            image_name="nexus/test-image",
            application_name="test-api",
            namespace="nexus",
            replicas=1,
        )

    assert result.status == "deployed"
    assert "created" in result.message
    apps_api.create_namespaced_deployment.assert_called_once()
    core_api.create_namespaced_service.assert_called_once()


def test_deploy_updates_existing_resources():
    apps_api = MagicMock()
    core_api = MagicMock()

    conflict = ApiException(status=409, reason="AlreadyExists")

    apps_api.create_namespaced_deployment.side_effect = conflict
    core_api.create_namespaced_service.side_effect = conflict

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.AppsV1Api",
            return_value=apps_api,
        ),
        patch(
            "app.services.kubernetes_deployer.client.CoreV1Api",
            return_value=core_api,
        ),
    ):
        result = deploy_application(
            image_name="nexus/test-image",
            application_name="test-api",
            namespace="nexus",
            replicas=1,
        )

    assert result.status == "deployed"
    assert "updated" in result.message
    apps_api.patch_namespaced_deployment.assert_called_once()
    core_api.patch_namespaced_service.assert_called_once()


def test_get_deployment_status_running():
    apps_api = MagicMock()

    deployment = MagicMock()
    deployment.spec.replicas = 1
    deployment.status.ready_replicas = 1
    deployment.status.available_replicas = 1

    apps_api.read_namespaced_deployment.return_value = deployment

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.AppsV1Api",
            return_value=apps_api,
        ),
    ):
        result = get_deployment_status(
            application_name="test-api",
            namespace="nexus",
        )

    assert result["status"] == "running"
    assert result["desired_replicas"] == 1
    assert result["ready_replicas"] == 1
    assert result["available_replicas"] == 1

    apps_api.read_namespaced_deployment.assert_called_once_with(
        name="test-api",
        namespace="nexus",
    )


def test_get_deployment_status_pending():
    apps_api = MagicMock()

    deployment = MagicMock()
    deployment.spec.replicas = 1
    deployment.status.ready_replicas = 0
    deployment.status.available_replicas = 0

    apps_api.read_namespaced_deployment.return_value = deployment

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.AppsV1Api",
            return_value=apps_api,
        ),
    ):
        result = get_deployment_status(
            application_name="test-api",
            namespace="nexus",
        )

    assert result["status"] == "pending"
    assert result["desired_replicas"] == 1
    assert result["ready_replicas"] == 0
    assert result["available_replicas"] == 0


def test_get_deployment_status_not_found():
    apps_api = MagicMock()

    not_found = ApiException(status=404, reason="NotFound")
    apps_api.read_namespaced_deployment.side_effect = not_found

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.AppsV1Api",
            return_value=apps_api,
        ),
    ):
        try:
            get_deployment_status(
                application_name="missing-api",
                namespace="nexus",
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert str(exc) == "Kubernetes deployment not found"