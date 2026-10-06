from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project
from app.schemas.build_plan import BuildPlanResponse
from app.services.blueprint import generate_blueprint
from app.services.build_plan import generate_build_plan
from app.services.github import github_service
from app.services.repository_analyzer import analyze_repository

router = APIRouter(
    prefix="/projects",
    tags=["Build Plans"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/{project_id}/build-plan",
    response_model=BuildPlanResponse,
)
async def create_build_plan(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if not project.repository_url:
        raise HTTPException(
            status_code=400,
            detail="Project has no repository URL",
        )

    try:
        repository = await github_service.get_repository(
            project.repository_url
        )

        paths = await github_service.get_repository_tree(
            repository["repository_url"],
            repository["default_branch"],
        )

        analysis = analyze_repository(paths)
        blueprint = generate_blueprint(analysis)

        plan = generate_build_plan(
            blueprint,
            project.name,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return BuildPlanResponse(
        project_id=project.id,
        project_name=project.name,
        build_type=plan.build_type,
        dockerfile_required=plan.dockerfile_required,
        image_name=plan.image_name,
        target_environment=plan.target_environment,
        steps=plan.steps,
    )