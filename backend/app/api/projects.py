from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
):
    user = db.get(User, 1)

    if not user:
        user = User(
            username="demo",
            email="demo@nexus.local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    project = Project(
        name=project_data.name,
        description=project_data.description,
        repository_url=project_data.repository_url,
        owner_id=user.id,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_projects(
    db: Session = Depends(get_db),
):
    projects = db.scalars(
        select(Project).order_by(Project.id)
    ).all()

    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


@router.delete(
    "/{project_id}",
    status_code=204,
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()