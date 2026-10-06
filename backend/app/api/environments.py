from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.environment import Environment
from app.models.project import Project
from app.schemas.environment import EnvironmentCreate, EnvironmentResponse

router = APIRouter(
    prefix="/projects/{project_id}/environments",
    tags=["Environments"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=EnvironmentResponse,
    status_code=201,
)
def create_environment(
    project_id: int,
    environment_data: EnvironmentCreate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    environment = Environment(
        name=environment_data.name,
        project_id=project_id,
    )

    db.add(environment)
    db.commit()
    db.refresh(environment)

    return environment


@router.get(
    "",
    response_model=list[EnvironmentResponse],
)
def list_environments(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    environments = db.scalars(
        select(Environment)
        .where(Environment.project_id == project_id)
        .order_by(Environment.id)
    ).all()

    return environments


@router.get(
    "/{environment_id}",
    response_model=EnvironmentResponse,
)
def get_environment(
    project_id: int,
    environment_id: int,
    db: Session = Depends(get_db),
):
    environment = db.scalar(
        select(Environment).where(
            Environment.id == environment_id,
            Environment.project_id == project_id,
        )
    )

    if not environment:
        raise HTTPException(
            status_code=404,
            detail="Environment not found",
        )

    return environment