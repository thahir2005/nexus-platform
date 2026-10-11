from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str

    gitops_enabled: bool = False
    gitops_repo_url: str = (
        "https://github.com/thahir2005/nexus-platform.git"
    )
    gitops_branch: str = "main"
    gitops_root_path: str = "infrastructure/gitops/apps"
    gitops_push: bool = True

    application_health_url: str | None = None
    application_health_timeout_seconds: float = 3.0

    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        extra="ignore",
    )


settings = Settings()