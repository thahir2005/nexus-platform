from pydantic import BaseModel


class DeploymentBlueprintResponse(BaseModel):
    repository_url: str
    application_type: str
    build_strategy: str
    containerization: str
    ci_cd: str
    kubernetes: str
    helm: str
    recommended_environment: str
    deployment_mode: str