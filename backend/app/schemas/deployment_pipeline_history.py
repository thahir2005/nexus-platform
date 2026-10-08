from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeploymentPipelineHistoryResponse(BaseModel):
    id: int
    project_id: int
    repository_path: str
    image_name: str
    application_name: str
    namespace: str
    replicas: int
    build_id: int
    security_scan_id: int | None
    deployment_id: int | None
    status: str
    build_status: str
    validation_status: str
    security_status: str
    high_count: int
    critical_count: int
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
