from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.docker_validation import (
    DockerValidationRequest,
    DockerValidationResponse,
)
from app.services.docker_validator import validate_image

router = APIRouter(
    prefix="/docker",
    tags=["Docker"],
)


@router.post(
    "/validate",
    response_model=DockerValidationResponse,
)
def docker_validate(
    request: DockerValidationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == user.id,
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    image_name = f"nexus/project-{project.id}"

    try:
        result = validate_image(image_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DockerValidationResponse(
        status=result.status,
        image_name=result.image_name,
        image_id=result.image_id,
        architecture=result.architecture,
        os=result.os,
        size=result.size,
        message=result.message,
    )
