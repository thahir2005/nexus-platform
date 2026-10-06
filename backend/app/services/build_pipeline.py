from dataclasses import dataclass

from app.services.docker_executor import build_image
from app.services.docker_validator import validate_image


@dataclass
class BuildPipelineResult:
    status: str
    image_name: str
    build_status: str
    validation_status: str
    architecture: str | None
    os: str | None
    message: str


def run_build_pipeline(
    repository_path: str,
    image_name: str,
) -> BuildPipelineResult:
    build_result = build_image(
        repository_path=repository_path,
        image_name=image_name,
    )

    if build_result.status != "success":
        return BuildPipelineResult(
            status="failed",
            image_name=image_name,
            build_status=build_result.status,
            validation_status="not_run",
            architecture=None,
            os=None,
            message="Docker image build failed",
        )

    validation_result = validate_image(image_name)

    if validation_result.status != "valid":
        return BuildPipelineResult(
            status="failed",
            image_name=image_name,
            build_status=build_result.status,
            validation_status=validation_result.status,
            architecture=validation_result.architecture,
            os=validation_result.os,
            message="Docker image validation failed",
        )

    return BuildPipelineResult(
        status="success",
        image_name=image_name,
        build_status=build_result.status,
        validation_status=validation_result.status,
        architecture=validation_result.architecture,
        os=validation_result.os,
        message="Build and image validation completed successfully",
    )