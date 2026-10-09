from typing import Any

from kubernetes import client, config


class ArgoCDService:
    def __init__(
        self,
        namespace: str = "argocd",
        application_name: str = "nexus-gitops-apps",
    ):
        self.namespace = namespace
        self.application_name = application_name

    def get_status(self) -> dict[str, Any]:
        try:
            config.load_kube_config()

            api = client.CustomObjectsApi()

            application = api.get_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace=self.namespace,
                plural="applications",
                name=self.application_name,
            )

            status = application.get("status", {})
            sync = status.get("sync", {})
            health = status.get("health", {})
            operation = status.get("operationState", {})

            return {
                "status": "available",
                "application_name": self.application_name,
                "sync_status": sync.get("status", "Unknown"),
                "health_status": health.get("status", "Unknown"),
                "revision": sync.get("revision"),
                "operation_phase": operation.get("phase"),
                "operation_message": operation.get("message"),
            }

        except Exception as exc:
            return {
                "status": "unavailable",
                "application_name": self.application_name,
                "sync_status": "Unknown",
                "health_status": "Unknown",
                "revision": None,
                "operation_phase": None,
                "operation_message": str(exc),
            }
