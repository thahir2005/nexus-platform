
from pydantic import BaseModel

class DeploymentPipelineRequest(BaseModel):
    environment_id: int

class DeploymentPipelineResponse(BaseModel):

    status: str

    project_id: int

    environment_id: int

    image_name: str

    build_id: int

    security_scan_id: int | None

    deployment_id: int | None

    deployment_name: str | None

    service_name: str | None

    namespace: str

    replicas: int

    build_status: str

    validation_status: str

    security_status: str

    high_count: int

    critical_count: int

    message: str
