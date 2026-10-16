from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic import BaseModel, Field


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentCreate(BaseModel):
    version: str


class DeploymentStatusUpdate(BaseModel):
    status: DeploymentStatus


class DeploymentResponse(BaseModel):
    id: int
    version: str
    status: DeploymentStatus
    environment_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class KubernetesDeployRequest(BaseModel):
    image_name: str = Field(
        pattern=r"^nexus/project-[1-9][0-9]*$",
        max_length=100,
    )
    application_name: str = Field(
        pattern=r"^nexus-project-[1-9][0-9]*$",
        max_length=63,
    )
    namespace: str = Field(
        default="nexus",
        pattern=r"^nexus$",
    )
    replicas: int = Field(default=1, ge=1, le=3)

class KubernetesDeployResponse(BaseModel):

    status: str

    project_id: int

    namespace: str

    deployment_name: str

    service_name: str

    replicas: int

    message: str

class KubernetesDeploymentResponse(BaseModel):
    id: int
    project_id: int
    environment_id: int | None
    image_name: str
    application_name: str
    namespace: str
    replicas: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class KubernetesDeploymentStatusResponse(BaseModel):
    deployment_id: int
    status: str
    desired_replicas: int
    ready_replicas: int
    available_replicas: int

class KubernetesDeploymentHealthResponse(BaseModel):
    deployment_id: int
    status: str
    pod_count: int
    healthy_pods: int
    unhealthy_pods: int
    pods: list[dict]