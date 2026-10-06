from fastapi import APIRouter, HTTPException

from app.schemas.build_pipeline import (
    BuildPipelineRequest,
    BuildPipelineResponse,
)
from app.services.build_pipeline import run_build_pipeline

router = APIRouter(
    prefix="/docker",
    tags=["Docker Pipeline"],
)


@router.post(
    "/pipeline",
    response_model=BuildPipelineResponse,
)
def docker_pipeline(
    request: BuildPipelineRequest,
):
    try:
        result = run_build_pipeline(
            repository_path=request.repository_path,
            image_name=request.image_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return BuildPipelineResponse(
        status=result.status,
        image_name=result.image_name,
        build_status=result.build_status,
        validation_status=result.validation_status,
        architecture=result.architecture,
        os=result.os,
        message=result.message,
    )