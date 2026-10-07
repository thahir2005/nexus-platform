from fastapi import APIRouter

from app.schemas.deployment import (
    KubernetesDeployRequest,
    KubernetesDeployResponse,
)
from app.services.kubernetes_deployer import deploy_application


router = APIRouter(
    prefix="/api/v1",
    tags=["kubernetes"],
)


@router.post(
    "/projects/{project_id}/deploy",
    response_model=KubernetesDeployResponse,
)
def deploy_project(
    project_id: int,
    request: KubernetesDeployRequest,
):
    result = deploy_application(
        image_name=request.image_name,
        application_name=request.application_name,
        namespace=request.namespace,
        replicas=request.replicas,
    )

    return KubernetesDeployResponse(
        status=result.status,
        project_id=project_id,
        namespace=result.namespace,
        deployment_name=result.deployment_name,
        service_name=result.service_name,
        replicas=request.replicas,
        message=result.message,
    )