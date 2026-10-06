from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SecurityScanResponse(BaseModel):
    id: int
    project_id: int
    build_id: int | None
    image_name: str
    status: str
    unknown_count: int
    low_count: int
    medium_count: int
    high_count: int
    critical_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)