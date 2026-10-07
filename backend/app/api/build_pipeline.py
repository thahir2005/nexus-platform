from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project
from app.schemas.build_pipeline import (
    BuildPipelineRequest,
    BuildPipelineResponse,
)
from app.services.build_pipeline import run_build_pipeline

router = APIRouter(
    prefix="/docker",
    tags=["Docker Pipeline"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/pipeline",
    response_model=BuildPipelineResponse,
)
def docker_pipeline(
    request: BuildPipelineRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, request.project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    try:
        result = run_build_pipeline(
            db=db,
            project_id=project.id,
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
        build_id=result.build_id,
        security_status=result.security_status,
        high_count=result.high_count,
        critical_count=result.critical_count,
        security_scan_id=result.security_scan_id,
    )