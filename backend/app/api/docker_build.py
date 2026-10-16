from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.docker_build import (
    DockerBuildRequest,
    DockerBuildResponse,
)
from app.services.docker_executor import build_image
from app.services.repository_workspace import prepare_repository_workspace


router = APIRouter(
    prefix="/docker",
    tags=["Docker"],
)


@router.post(
    "/build",
    response_model=DockerBuildResponse,
)
def docker_build(
    request: DockerBuildRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == user.id,
    ).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        repository_path = prepare_repository_workspace(project)
        result = build_image(
            repository_path=repository_path,
            image_name=f"nexus/project-{project.id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DockerBuildResponse(
        status=result.status,
        image_name=result.image_name,
        output=result.output,
    )