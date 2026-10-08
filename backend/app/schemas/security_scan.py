from datetime import datetime

from pydantic import BaseModel, ConfigDict

class SecurityFinding(BaseModel):
    vulnerability_id: str | None = None
    package: str | None = None
    installed_version: str | None = None
    fixed_version: str | None = None
    severity: str
    title: str | None = None
    target: str | None = None

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
    findings: list[SecurityFinding] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
