from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.auth import get_current_user
from app.models.user import User
from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.project import Project
from app.schemas.deployment_pipeline_history import (
    DeploymentPipelineHistoryResponse,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["deployment history"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/projects/{project_id}/deployment-history",
    response_model=list[DeploymentPipelineHistoryResponse],
)
def get_deployment_history(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id)
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return (
        db.query(DeploymentPipelineRun)
        .filter(DeploymentPipelineRun.project_id == project_id)
        .order_by(DeploymentPipelineRun.created_at.desc())
        .all()
    )
