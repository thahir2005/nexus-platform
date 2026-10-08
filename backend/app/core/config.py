from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    gitops_enabled: bool = False
    gitops_repo_url: str = "https://github.com/thahir2005/nexus-platform.git"
    gitops_branch: str = "main"
    gitops_root_path: str = "infrastructure/gitops/apps"
    gitops_push: bool = True

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
