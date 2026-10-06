from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildResponse(BaseModel):
    id: int
    project_id: int
    image_name: str
    status: str
    build_status: str
    validation_status: str
    architecture: str | None
    os: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)