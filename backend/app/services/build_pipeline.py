from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.build import Build
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
    build_id: int


def run_build_pipeline(
    db: Session,
    project_id: int,
    repository_path: str,
    image_name: str,
) -> BuildPipelineResult:

    build_result = build_image(
        repository_path=repository_path,
        image_name=image_name,
    )

    # Create a persistent build record immediately after the Docker build.
    build_record = Build(
        project_id=project_id,
        image_name=image_name,
        status=build_result.status,
        build_status=build_result.status,
        validation_status="not_run",
    )

    db.add(build_record)
    db.commit()
    db.refresh(build_record)

    if build_result.status != "success":
        return BuildPipelineResult(
            status="failed",
            image_name=image_name,
            build_status=build_result.status,
            validation_status="not_run",
            architecture=None,
            os=None,
            message="Docker image build failed",
            build_id=build_record.id,
        )

    validation_result = validate_image(image_name)

    build_record.validation_status = validation_result.status
    build_record.architecture = validation_result.architecture
    build_record.os = validation_result.os

    if validation_result.status != "valid":
        build_record.status = "failed"
        db.commit()

        return BuildPipelineResult(
            status="failed",
            image_name=image_name,
            build_status=build_result.status,
            validation_status=validation_result.status,
            architecture=validation_result.architecture,
            os=validation_result.os,
            message="Docker image validation failed",
            build_id=build_record.id,
        )

    build_record.status = "success"
    db.commit()

    return BuildPipelineResult(
        status="success",
        image_name=image_name,
        build_status=build_result.status,
        validation_status=validation_result.status,
        architecture=validation_result.architecture,
        os=validation_result.os,
        message="Build and image validation completed successfully",
        build_id=build_record.id,
    )