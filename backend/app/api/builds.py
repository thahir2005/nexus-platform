from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.auth import get_current_user
from app.models.user import User
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
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id)
        .first()
    )

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
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

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