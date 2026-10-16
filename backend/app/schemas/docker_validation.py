from pydantic import BaseModel, Field


class DockerValidationRequest(BaseModel):
    project_id: int = Field(gt=0)


class DockerValidationResponse(BaseModel):
    status: str
    image_name: str
    image_id: str | None
    architecture: str | None
    os: str | None
    size: str | None
    message: str
