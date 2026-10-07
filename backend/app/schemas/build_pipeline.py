from pydantic import BaseModel


class BuildPipelineRequest(BaseModel):
    project_id: int
    repository_path: str
    image_name: str


class BuildPipelineResponse(BaseModel):
    build_id: int
    status: str
    image_name: str
    build_status: str
    validation_status: str
    architecture: str | None
    os: str | None
    message: str
    security_status: str
    high_count: int
    critical_count: int
    security_scan_id: int | None