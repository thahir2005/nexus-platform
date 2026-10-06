from fastapi import APIRouter, HTTPException

from app.schemas.docker_build import (
    DockerBuildRequest,
    DockerBuildResponse,
)
from app.services.docker_executor import build_image

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
):
    try:
        result = build_image(
            repository_path=request.repository_path,
            image_name="nexus/local-build",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DockerBuildResponse(
        status=result.status,
        image_name=result.image_name,
        output=result.output,
    )