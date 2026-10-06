from fastapi import APIRouter, HTTPException

from app.schemas.blueprint import DeploymentBlueprintResponse
from app.schemas.github import GitHubImportRequest
from app.services.blueprint import generate_blueprint
from app.services.github import github_service
from app.services.repository_analyzer import analyze_repository

router = APIRouter(
    prefix="/repository",
    tags=["Deployment Blueprint"],
)


@router.post(
    "/blueprint",
    response_model=DeploymentBlueprintResponse,
)
async def generate_repository_blueprint(
    import_data: GitHubImportRequest,
):
    try:
        repository = await github_service.get_repository(
            import_data.repository_url
        )

        paths = await github_service.get_repository_tree(
            repository["repository_url"],
            repository["default_branch"],
        )

        analysis = analyze_repository(paths)

        blueprint = generate_blueprint(analysis)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DeploymentBlueprintResponse(
        repository_url=repository["repository_url"],
        application_type=blueprint.application_type,
        build_strategy=blueprint.build_strategy,
        containerization=blueprint.containerization,
        ci_cd=blueprint.ci_cd,
        kubernetes=blueprint.kubernetes,
        helm=blueprint.helm,
        recommended_environment=blueprint.recommended_environment,
        deployment_mode=blueprint.deployment_mode,
    )