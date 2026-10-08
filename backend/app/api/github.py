from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.environment import Environment
from app.models.user import User
from app.schemas.github import (
    GitHubImportRequest,
    GitHubImportResponse,
)
from app.schemas.project import ProjectResponse
from app.services.github import github_service

router = APIRouter(
    prefix="/projects/import",
    tags=["GitHub Import"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/github",
    response_model=ProjectResponse,
    status_code=201,
)
async def import_github_repository(
    import_data: GitHubImportRequest,
    db: Session = Depends(get_db),
):
    try:
        repository = await github_service.get_repository(
            import_data.repository_url
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    existing_project = db.scalar(
        select(Project).where(
            Project.repository_url == repository["repository_url"]
        )
    )

    if existing_project:
        return existing_project

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
        name=repository["name"],
        description=repository["description"],
        repository_url=repository["repository_url"],
        owner_id=user.id,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    development = Environment(
        name="development",
        project_id=project.id,
    )

    staging = Environment(
        name="staging",
        project_id=project.id,
    )

    db.add_all([development, staging])
    db.commit()

    return project