from pydantic import BaseModel


class BuildPipelineRequest(BaseModel):
    repository_path: str
    image_name: str


class BuildPipelineResponse(BaseModel):
    status: str
    image_name: str
    build_status: str
    validation_status: str
    architecture: str | None
    os: str | None
    message: str