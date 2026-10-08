from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.build import Build
from app.models.security_scan import SecurityScan
from app.services.docker_executor import build_image
from app.services.docker_validator import validate_image
from app.services.trivy_scanner import scan_image


@dataclass
class BuildPipelineResult:
    status: str
    image_name: str
    build_status: str
    validation_status: str
    security_status: str
    architecture: str | None
    os: str | None
    high_count: int
    critical_count: int
    message: str
    build_id: int
    security_scan_id: int | None


def run_build_pipeline(
    db: Session,
    project_id: int,
    repository_path: str,
    image_name: str,
) -> BuildPipelineResult:

    # 1. Build Docker image
    build_result = build_image(
        repository_path=repository_path,
        image_name=image_name,
    )

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
            security_status="not_run",
            architecture=None,
            os=None,
            high_count=0,
            critical_count=0,
            message="Docker image build failed",
            build_id=build_record.id,
            security_scan_id=None,
        )

    # 2. Validate Docker image
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
            security_status="not_run",
            architecture=validation_result.architecture,
            os=validation_result.os,
            high_count=0,
            critical_count=0,
            message="Docker image validation failed",
            build_id=build_record.id,
            security_scan_id=None,
        )

    # 3. Trivy security scan
    security_result = scan_image(image_name)

    security_scan = SecurityScan(
        project_id=project_id,
        build_id=build_record.id,
        image_name=image_name,
        status=security_result.status,
        unknown_count=security_result.unknown_count,
        low_count=security_result.low_count,
        medium_count=security_result.medium_count,
        high_count=security_result.high_count,
        critical_count=security_result.critical_count,
        findings=security_result.findings,
    )

    db.add(security_scan)
    db.commit()
    db.refresh(security_scan)

    # 4. Security gate
    if security_result.status == "blocked":
        build_record.status = "failed"
        db.commit()

        return BuildPipelineResult(
            status="failed",
            image_name=image_name,
            build_status=build_result.status,
            validation_status=validation_result.status,
            security_status=security_result.status,
            architecture=validation_result.architecture,
            os=validation_result.os,
            high_count=security_result.high_count,
            critical_count=security_result.critical_count,
            message=security_result.message,
            build_id=build_record.id,
            security_scan_id=security_scan.id,
        )

    # 5. Pipeline succeeded
    build_record.status = "success"
    db.commit()

    return BuildPipelineResult(
        status="success",
        image_name=image_name,
        build_status=build_result.status,
        validation_status=validation_result.status,
        security_status=security_result.status,
        architecture=validation_result.architecture,
        os=validation_result.os,
        high_count=security_result.high_count,
        critical_count=security_result.critical_count,
        message="Build, validation, and security scan completed successfully",
        build_id=build_record.id,
        security_scan_id=security_scan.id,
    )