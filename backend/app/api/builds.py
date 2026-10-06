from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.build import Build
from app.models.project import Project
from app.schemas.build import BuildResponse

router = APIRouter(
    prefix="/projects",
    tags=["Build History"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/{project_id}/builds",
    response_model=list[BuildResponse],
)
def list_builds(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return (
        db.query(Build)
        .filter(Build.project_id == project_id)
        .order_by(Build.created_at.desc())
        .all()
    )


@router.get(
    "/{project_id}/builds/{build_id}",
    response_model=BuildResponse,
)
def get_build(
    project_id: int,
    build_id: int,
    db: Session = Depends(get_db),
):
    build = (
        db.query(Build)
        .filter(
            Build.id == build_id,
            Build.project_id == project_id,
        )
        .first()
    )

    if not build:
        raise HTTPException(
            status_code=404,
            detail="Build not found",
        )

    return build