from pydantic import BaseModel


class RepositoryAnalysisResponse(BaseModel):
    repository_url: str
    languages: list[str]
    frameworks: list[str]
    has_dockerfile: bool
    has_ci: bool
    has_kubernetes: bool
    has_helm: bool
    has_tests: bool
    has_readme: bool