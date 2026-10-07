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
from app.services.kubernetes_deployer import deploy_application


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