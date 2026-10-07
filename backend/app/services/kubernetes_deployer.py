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