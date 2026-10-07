from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.project import Project
from app.schemas.deployment import (
    KubernetesDeployRequest,
    KubernetesDeployResponse,
    KubernetesDeploymentResponse,
)
from app.services.kubernetes_deployer import (
    deploy_application,
    get_deployment_status,
    get_pod_health,
)
from app.schemas.deployment import (
    KubernetesDeployRequest,
    KubernetesDeployResponse,
    KubernetesDeploymentResponse,
    KubernetesDeploymentStatusResponse,
)

from app.schemas.deployment import (
    KubernetesDeployRequest,
    KubernetesDeployResponse,
    KubernetesDeploymentResponse,
    KubernetesDeploymentStatusResponse,
    KubernetesDeploymentHealthResponse,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["kubernetes"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/projects/{project_id}/deploy",
    response_model=KubernetesDeployResponse,
)
def deploy_project(
    project_id: int,
    request: KubernetesDeployRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    result = deploy_application(
        image_name=request.image_name,
        application_name=request.application_name,
        namespace=request.namespace,
        replicas=request.replicas,
    )

    deployment = KubernetesDeployment(
        project_id=project_id,
        image_name=request.image_name,
        application_name=result.deployment_name,
        namespace=result.namespace,
        replicas=request.replicas,
        status=result.status,
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    return KubernetesDeployResponse(
        status=result.status,
        project_id=project_id,
        namespace=result.namespace,
        deployment_name=result.deployment_name,
        service_name=result.service_name,
        replicas=request.replicas,
        message=result.message,
    )


@router.get(
    "/projects/{project_id}/deployments",
    response_model=list[KubernetesDeploymentResponse],
)
def get_project_deployments(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    deployments = (
        db.query(KubernetesDeployment)
        .filter(KubernetesDeployment.project_id == project_id)
        .order_by(KubernetesDeployment.created_at.desc())
        .all()
    )

    return deployments

@router.get(
    "/projects/{project_id}/deployments/{deployment_id}/status",
    response_model=KubernetesDeploymentStatusResponse,
)
def get_project_deployment_status(
    project_id: int,
    deployment_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    deployment = db.get(KubernetesDeployment, deployment_id)

    if deployment is None or deployment.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    result = get_deployment_status(
        application_name=deployment.application_name,
        namespace=deployment.namespace,
    )

    deployment.status = result["status"]

    db.commit()
    db.refresh(deployment)

    return KubernetesDeploymentStatusResponse(
        deployment_id=deployment.id,
        status=result["status"],
        desired_replicas=result["desired_replicas"],
        ready_replicas=result["ready_replicas"],
        available_replicas=result["available_replicas"],
    )

@router.get(
    "/projects/{project_id}/deployments/{deployment_id}/health",
    response_model=KubernetesDeploymentHealthResponse,
)
def get_project_deployment_health(
    project_id: int,
    deployment_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    deployment = db.get(KubernetesDeployment, deployment_id)

    if deployment is None or deployment.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    result = get_pod_health(
        application_name=deployment.application_name,
        namespace=deployment.namespace,
    )

    return KubernetesDeploymentHealthResponse(
        deployment_id=deployment.id,
        status=result["status"],
        pod_count=result["pod_count"],
        healthy_pods=result["healthy_pods"],
        unhealthy_pods=result["unhealthy_pods"],
        pods=result["pods"],
    )