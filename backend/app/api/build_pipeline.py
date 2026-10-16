from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.build_pipeline import (
    BuildPipelineRequest,
    BuildPipelineResponse,
)
from app.services.build_pipeline import run_build_pipeline
from app.services.repository_workspace import prepare_repository_workspace


router = APIRouter(
    prefix="/docker",
    tags=["Docker Pipeline"],
)


@router.post("/pipeline", response_model=BuildPipelineResponse)
def docker_pipeline(
    request: BuildPipelineRequest,
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

        # The client cannot choose the image namespace or tag.
        image_name = f"nexus/project-{project.id}"

        result = run_build_pipeline(
            db=db,
            project_id=project.id,
            repository_path=repository_path,
            image_name=image_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BuildPipelineResponse(
        status=result.status,
        image_name=result.image_name,
        build_status=result.build_status,
        validation_status=result.validation_status,
        architecture=result.architecture,
        os=result.os,
        message=result.message,
        build_id=result.build_id,
        security_status=result.security_status,
        high_count=result.high_count,
        critical_count=result.critical_count,
        security_scan_id=result.security_scan_id,
    )
