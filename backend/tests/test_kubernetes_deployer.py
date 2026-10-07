from unittest.mock import MagicMock, patch

from kubernetes.client.exceptions import ApiException

from app.services.kubernetes_deployer import deploy_application


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