import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from app.models.project import Project


WORKSPACE_ROOT = Path("/tmp/nexus-workspaces")


def _validate_github_url(repository_url: str) -> None:
    parsed = urlparse(repository_url)

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS GitHub repositories are supported.")

    if parsed.netloc.lower() != "github.com":
        raise ValueError("Only GitHub repositories are supported.")


def prepare_repository_workspace(project: Project) -> str:
    if not project.repository_url:
        raise ValueError("Project does not have a GitHub repository.")

    _validate_github_url(project.repository_url)

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    workspace = WORKSPACE_ROOT / f"project-{project.id}"

    if workspace.exists():
        shutil.rmtree(workspace)

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                project.repository_url,
                str(workspace),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Unable to clone repository: {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Repository clone timed out.") from exc

    return str(workspace)