from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.deployment import Deployment
from app.models.environment import Environment
from app.models.project import Project
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentStatus,
    DeploymentStatusUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/environments/{environment_id}/deployments",
    tags=["Deployments"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ALLOWED_TRANSITIONS = {
    DeploymentStatus.PENDING: {
        DeploymentStatus.RUNNING,
        DeploymentStatus.FAILED,
    },
    DeploymentStatus.RUNNING: {
        DeploymentStatus.SUCCESS,
        DeploymentStatus.FAILED,
    },
    DeploymentStatus.SUCCESS: {
        DeploymentStatus.ROLLED_BACK,
    },
    DeploymentStatus.FAILED: {
        DeploymentStatus.PENDING,
    },
    DeploymentStatus.ROLLED_BACK: set(),
}


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=201,
)
def create_deployment(
    project_id: int,
    environment_id: int,
    deployment_data: DeploymentCreate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    environment = db.scalar(
        select(Environment).where(
            Environment.id == environment_id,
            Environment.project_id == project_id,
        )
    )

    if not environment:
        raise HTTPException(
            status_code=404,
            detail="Environment not found",
        )

    deployment = Deployment(
        version=deployment_data.version,
        status=DeploymentStatus.PENDING.value,
        environment_id=environment_id,
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    return deployment


@router.get(
    "",
    response_model=list[DeploymentResponse],
)
def list_deployments(
    project_id: int,
    environment_id: int,
    db: Session = Depends(get_db),
):
    environment = db.scalar(
        select(Environment).where(
            Environment.id == environment_id,
            Environment.project_id == project_id,
        )
    )

    if not environment:
        raise HTTPException(
            status_code=404,
            detail="Environment not found",
        )

    return db.scalars(
        select(Deployment)
        .where(Deployment.environment_id == environment_id)
        .order_by(Deployment.id)
    ).all()


@router.get(
    "/{deployment_id}",
    response_model=DeploymentResponse,
)
def get_deployment(
    project_id: int,
    environment_id: int,
    deployment_id: int,
    db: Session = Depends(get_db),
):
    deployment = db.scalar(
        select(Deployment)
        .join(Environment)
        .where(
            Deployment.id == deployment_id,
            Deployment.environment_id == environment_id,
            Environment.project_id == project_id,
        )
    )

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    return deployment


@router.patch(
    "/{deployment_id}/status",
    response_model=DeploymentResponse,
)
def update_deployment_status(
    project_id: int,
    environment_id: int,
    deployment_id: int,
    status_data: DeploymentStatusUpdate,
    db: Session = Depends(get_db),
):
    deployment = db.scalar(
        select(Deployment)
        .join(Environment)
        .where(
            Deployment.id == deployment_id,
            Deployment.environment_id == environment_id,
            Environment.project_id == project_id,
        )
    )

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    current_status = DeploymentStatus(deployment.status)
    requested_status = status_data.status

    if requested_status not in ALLOWED_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Invalid deployment transition: "
                f"{current_status.value} -> {requested_status.value}"
            ),
        )

    deployment.status = requested_status.value

    db.commit()
    db.refresh(deployment)

    return deployment