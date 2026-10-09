from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeploymentPipelineStatus(BaseModel):
    id: int
    status: str
    build_id: int
    security_scan_id: int | None
    build_status: str
    validation_status: str
    security_status: str
    high_count: int
    critical_count: int
    message: str
    created_at: datetime


class GitOpsStatus(BaseModel):
    status: str
    revision: str | None = None


class KubernetesStatus(BaseModel):
    status: str
    deployment_name: str
    namespace: str
    desired_replicas: int
    ready_replicas: int
    available_replicas: int


class ArgoCDStatus(BaseModel):
    status: str
    application_name: str
    sync_status: str
    health_status: str
    revision: str | None = None
    operation_phase: str | None = None
    operation_message: str | None = None


class DeploymentStatusResponse(BaseModel):
    project_id: int
    environment_id: int
    environment_name: str
    image_name: str
    application_name: str
    pipeline: DeploymentPipelineStatus
    gitops: GitOpsStatus
    argo: ArgoCDStatus
    kubernetes: KubernetesStatus
