from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


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

    image_name: str

    application_name: str

    namespace: str = "nexus"

    replicas: int = 1

class KubernetesDeployResponse(BaseModel):

    status: str

    project_id: int

    namespace: str

    deployment_name: str

    service_name: str

    replicas: int

    message: str