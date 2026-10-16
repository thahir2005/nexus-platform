from pydantic import BaseModel, Field


class DockerBuildRequest(BaseModel):
    project_id: int = Field(gt=0)


class DockerBuildResponse(BaseModel):
    status: str
    image_name: str
    output: str