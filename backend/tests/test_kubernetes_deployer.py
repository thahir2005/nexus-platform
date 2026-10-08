from unittest.mock import MagicMock, patch

from kubernetes.client.exceptions import ApiException

from app.services.kubernetes_deployer import (
    deploy_application,
    get_deployment_status,
    get_pod_health,
)


def test_deploy_creates_resources():
    apps_api = MagicMock()
    core_api = MagicMock()

    apps_api.read_namespaced_deployment.return_value.status.ready_replicas = 1
    apps_api.read_namespaced_deployment.return_value.status.available_replicas = 1

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer._load_local_image_into_minikube"
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

    apps_api.read_namespaced_deployment.return_value.status.ready_replicas = 1
    apps_api.read_namespaced_deployment.return_value.status.available_replicas = 1

    conflict = ApiException(status=409, reason="AlreadyExists")

    apps_api.create_namespaced_deployment.side_effect = conflict
    core_api.create_namespaced_service.side_effect = conflict

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer._load_local_image_into_minikube"
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

def test_get_pod_health_healthy():
    core_api = MagicMock()

    pod = MagicMock()
    pod.metadata.name = "test-api-pod"
    pod.status.phase = "Running"

    container = MagicMock()
    container.ready = True
    container.restart_count = 0
    container.state.waiting = None
    container.state.terminated = None

    pod.status.container_statuses = [container]

    pod_list = MagicMock()
    pod_list.items = [pod]

    core_api.list_namespaced_pod.return_value = pod_list

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.CoreV1Api",
            return_value=core_api,
        ),
    ):
        result = get_pod_health(
            application_name="test-api",
            namespace="nexus",
        )

    assert result["status"] == "healthy"
    assert result["pod_count"] == 1
    assert result["healthy_pods"] == 1
    assert result["unhealthy_pods"] == 0

    assert result["pods"][0]["name"] == "test-api-pod"
    assert result["pods"][0]["status"] == "Running"
    assert result["pods"][0]["ready"] is True
    assert result["pods"][0]["restart_count"] == 0
    assert result["pods"][0]["reason"] is None

    core_api.list_namespaced_pod.assert_called_once_with(
        namespace="nexus",
        label_selector="app=test-api",
    )


def test_get_pod_health_unhealthy():
    core_api = MagicMock()

    pod = MagicMock()
    pod.metadata.name = "test-api-pod"
    pod.status.phase = "Pending"

    container = MagicMock()
    container.ready = False
    container.restart_count = 3

    waiting_state = MagicMock()
    waiting_state.reason = "CrashLoopBackOff"

    container.state.waiting = waiting_state
    container.state.terminated = None

    pod.status.container_statuses = [container]

    pod_list = MagicMock()
    pod_list.items = [pod]

    core_api.list_namespaced_pod.return_value = pod_list

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.CoreV1Api",
            return_value=core_api,
        ),
    ):
        result = get_pod_health(
            application_name="test-api",
            namespace="nexus",
        )

    assert result["status"] == "unhealthy"
    assert result["pod_count"] == 1
    assert result["healthy_pods"] == 0
    assert result["unhealthy_pods"] == 1

    assert result["pods"][0]["status"] == "Pending"
    assert result["pods"][0]["ready"] is False
    assert result["pods"][0]["restart_count"] == 3
    assert result["pods"][0]["reason"] == "CrashLoopBackOff"


def test_get_pod_health_no_pods():
    core_api = MagicMock()

    pod_list = MagicMock()
    pod_list.items = []

    core_api.list_namespaced_pod.return_value = pod_list

    with (
        patch(
            "app.services.kubernetes_deployer.config.load_kube_config"
        ),
        patch(
            "app.services.kubernetes_deployer.client.CoreV1Api",
            return_value=core_api,
        ),
    ):
        result = get_pod_health(
            application_name="test-api",
            namespace="nexus",
        )

    assert result["status"] == "no_pods"
    assert result["pod_count"] == 0
    assert result["healthy_pods"] == 0
    assert result["unhealthy_pods"] == 0
    assert result["pods"] == []