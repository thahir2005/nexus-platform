from pydantic import BaseModel


class GitHubImportRequest(BaseModel):
    repository_url: str


class GitHubImportResponse(BaseModel):
    name: str
    description: str | None
    repository_url: str
    default_branch: str | None
    language: str | None
    visibility: str | None