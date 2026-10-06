from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    repository_url: str | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    repository_url: str | None
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)