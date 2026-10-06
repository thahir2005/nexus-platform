from fastapi import APIRouter, HTTPException

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
):
    try:
        result = validate_image(request.image_name)
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