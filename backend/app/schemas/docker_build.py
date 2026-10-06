from pydantic import BaseModel


class DockerBuildRequest(BaseModel):
    repository_path: str


class DockerBuildResponse(BaseModel):
    status: str
    image_name: str
    output: str