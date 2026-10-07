from dataclasses import dataclass

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


@dataclass
class KubernetesDeploymentResult:
    status: str
    namespace: str
    deployment_name: str
    service_name: str
    message: str


def deploy_application(
    image_name: str,
    application_name: str,
    namespace: str = "nexus",
    replicas: int = 1,
) -> KubernetesDeploymentResult:
    config.load_kube_config()

    apps_api = client.AppsV1Api()
    core_api = client.CoreV1Api()

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=application_name,
            namespace=namespace,
        ),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(
                match_labels={"app": application_name}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": application_name}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name=application_name,
                            image=image_name,
                            image_pull_policy="IfNotPresent",
                            ports=[
                                client.V1ContainerPort(
                                    container_port=8000
                                )
                            ],
                        )
                    ]
                ),
            ),
        ),
    )

    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=application_name,
            namespace=namespace,
        ),
        spec=client.V1ServiceSpec(
            selector={"app": application_name},
            ports=[
                client.V1ServicePort(
                    port=8000,
                    target_port=8000,
                )
            ],
            type="ClusterIP",
        ),
    )

    try:
        apps_api.create_namespaced_deployment(
            namespace=namespace,
            body=deployment,
        )
        deployment_status = "created"

    except ApiException as exc:
        if exc.status != 409:
            raise ValueError(
                f"Kubernetes deployment failed: {exc.reason}"
            ) from exc

        apps_api.patch_namespaced_deployment(
            name=application_name,
            namespace=namespace,
            body=deployment,
        )
        deployment_status = "updated"

    try:
        core_api.create_namespaced_service(
            namespace=namespace,
            body=service,
        )
        service_status = "created"

    except ApiException as exc:
        if exc.status != 409:
            raise ValueError(
                f"Kubernetes service failed: {exc.reason}"
            ) from exc

        core_api.patch_namespaced_service(
            name=application_name,
            namespace=namespace,
            body=service,
        )
        service_status = "updated"

    return KubernetesDeploymentResult(
        status="deployed",
        namespace=namespace,
        deployment_name=application_name,
        service_name=application_name,
        message=(
            f"Kubernetes deployment {deployment_status}; "
            f"service {service_status}"
        ),
    )

def get_deployment_status(
    application_name: str,
    namespace: str = "nexus",
) -> dict:
    config.load_kube_config()

    apps_api = client.AppsV1Api()

    try:
        deployment = apps_api.read_namespaced_deployment(
            name=application_name,
            namespace=namespace,
        )
    except ApiException as exc:
        if exc.status == 404:
            raise ValueError(
                "Kubernetes deployment not found"
            ) from exc

        raise ValueError(
            f"Unable to read Kubernetes deployment: {exc.reason}"
        ) from exc

    spec = deployment.spec
    status = deployment.status

    desired_replicas = spec.replicas or 0
    ready_replicas = status.ready_replicas or 0
    available_replicas = status.available_replicas or 0

    if ready_replicas == desired_replicas and desired_replicas > 0:
        deployment_status = "running"
    elif ready_replicas > 0:
        deployment_status = "degraded"
    else:
        deployment_status = "pending"

    return {
        "status": deployment_status,
        "desired_replicas": desired_replicas,
        "ready_replicas": ready_replicas,
        "available_replicas": available_replicas,
    }

def get_pod_health(
    application_name: str,
    namespace: str = "nexus",
) -> dict:
    config.load_kube_config()

    core_api = client.CoreV1Api()

    try:
        pods = core_api.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={application_name}",
        )
    except ApiException as exc:
        if exc.status == 404:
            raise ValueError(
                "Kubernetes namespace not found"
            ) from exc

        raise ValueError(
            f"Unable to read Kubernetes pods: {exc.reason}"
        ) from exc

    pod_details = []

    for pod in pods.items:
        phase = pod.status.phase or "Unknown"

        ready = False
        if pod.status.container_statuses:
            ready = all(
                container.ready
                for container in pod.status.container_statuses
            )

        restart_count = 0
        if pod.status.container_statuses:
            restart_count = sum(
                container.restart_count or 0
                for container in pod.status.container_statuses
            )

        reason = None

        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                state = container.state

                if state and state.waiting:
                    reason = state.waiting.reason
                    break

                if state and state.terminated:
                    reason = state.terminated.reason
                    break

        pod_details.append(
            {
                "name": pod.metadata.name,
                "status": phase,
                "ready": ready,
                "restart_count": restart_count,
                "reason": reason,
            }
        )

    healthy_pods = sum(
        1
        for pod in pod_details
        if pod["status"] == "Running" and pod["ready"]
    )

    unhealthy_pods = len(pod_details) - healthy_pods

    if not pod_details:
        health_status = "no_pods"
    elif unhealthy_pods == 0:
        health_status = "healthy"
    elif healthy_pods > 0:
        health_status = "degraded"
    else:
        health_status = "unhealthy"

    return {
        "status": health_status,
        "pod_count": len(pod_details),
        "healthy_pods": healthy_pods,
        "unhealthy_pods": unhealthy_pods,
        "pods": pod_details,
    }