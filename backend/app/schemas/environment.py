from pydantic import BaseModel, ConfigDict


class EnvironmentCreate(BaseModel):
    name: str


class EnvironmentResponse(BaseModel):
    id: int
    name: str
    project_id: int

    model_config = ConfigDict(from_attributes=True)