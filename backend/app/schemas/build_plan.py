from pydantic import BaseModel


class BuildPlanResponse(BaseModel):
    project_id: int
    project_name: str
    build_type: str
    dockerfile_required: bool
    image_name: str
    target_environment: str
    steps: list[str]