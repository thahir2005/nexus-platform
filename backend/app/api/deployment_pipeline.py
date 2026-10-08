from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project
from app.schemas.deployment_pipeline import (
    DeploymentPipelineRequest,
    DeploymentPipelineResponse,
)
from app.services.deployment_orchestrator import run_deployment_pipeline


router = APIRouter(
    prefix="/api/v1",
    tags=["deployment pipeline"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/projects/{project_id}/deploy-pipeline",
    response_model=DeploymentPipelineResponse,
)
def deploy_pipeline(
    project_id: int,
    request: DeploymentPipelineRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    try:
        result = run_deployment_pipeline(
            db=db,
            project_id=project_id,
            repository_path=request.repository_path,
            image_name=request.image_name,
            application_name=request.application_name,
            namespace=request.namespace,
            replicas=request.replicas,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DeploymentPipelineResponse(
        status=result.status,
        project_id=result.project_id,
        image_name=result.image_name,
        build_id=result.build_id,
        security_scan_id=result.security_scan_id,
        deployment_id=result.deployment_id,
        deployment_name=result.deployment_name,
        service_name=result.service_name,
        namespace=result.namespace,
        replicas=result.replicas,
        build_status=result.build_status,
        validation_status=result.validation_status,
        security_status=result.security_status,
        high_count=result.high_count,
        critical_count=result.critical_count,
        message=result.message,
    )
