from pydantic import BaseModel


class DockerValidationRequest(BaseModel):
    image_name: str


class DockerValidationResponse(BaseModel):
    status: str
    image_name: str
    image_id: str | None
    architecture: str | None
    os: str | None
    size: str | None
    message: str