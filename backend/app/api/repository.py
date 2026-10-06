from fastapi import APIRouter, HTTPException

from app.schemas.github import GitHubImportRequest
from app.schemas.repository import RepositoryAnalysisResponse
from app.services.github import github_service
from app.services.repository_analyzer import analyze_repository

router = APIRouter(
    prefix="/repository",
    tags=["Repository Intelligence"],
)


@router.post(
    "/analyze",
    response_model=RepositoryAnalysisResponse,
)
async def analyze_github_repository(
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

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return RepositoryAnalysisResponse(
        repository_url=repository["repository_url"],
        languages=analysis.languages,
        frameworks=analysis.frameworks,
        has_dockerfile=analysis.has_dockerfile,
        has_ci=analysis.has_ci,
        has_kubernetes=analysis.has_kubernetes,
        has_helm=analysis.has_helm,
        has_tests=analysis.has_tests,
        has_readme=analysis.has_readme,
    )