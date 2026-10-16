import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from app.models.project import Project


WORKSPACE_ROOT = Path("/tmp/nexus-workspaces").resolve()

_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def _validate_github_url(repository_url: str) -> None:
    """Accept only canonical HTTPS URLs for GitHub repositories."""
    if not isinstance(repository_url, str) or not repository_url:
        raise ValueError("A valid GitHub repository URL is required.")

    if any(ord(char) < 32 or char.isspace() for char in repository_url):
        raise ValueError("Invalid GitHub repository URL.")

    # Reject encoded paths and backslashes rather than relying on
    # different URL parsers to interpret them consistently.
    if "%" in repository_url or "\\" in repository_url:
        raise ValueError("Invalid GitHub repository URL.")

    try:
        parsed = urlparse(repository_url)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid GitHub repository URL.") from None

    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only canonical HTTPS GitHub repository URLs are supported.")

    parts = parsed.path.split("/")

    if (
        len(parts) != 3
        or parts[0] != ""
        or not parts[1]
        or not parts[2]
    ):
        raise ValueError("Invalid GitHub repository URL.")

    owner, repository = parts[1], parts[2]

    if repository.endswith(".git"):
        repository = repository[:-4]

    if (
        not _OWNER_PATTERN.fullmatch(owner)
        or not _REPOSITORY_PATTERN.fullmatch(repository)
        or repository in {".", ".."}
    ):
        raise ValueError("Invalid GitHub repository URL.")


def prepare_repository_workspace(project: Project) -> str:
    """Clone a project's GitHub repository into a unique workspace."""
    if not project.repository_url:
        raise ValueError("Project does not have a GitHub repository.")

    _validate_github_url(project.repository_url)

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    root = WORKSPACE_ROOT.resolve()

    workspace = Path(
        tempfile.mkdtemp(
            prefix=f"project-{project.id}-",
            dir=str(root),
        )
    ).resolve()

    # Ensure cleanup and clone operations remain confined to our workspace root.
    if workspace.parent != root:
        raise ValueError("Invalid repository workspace path.")

    workspace.rmdir()

    try:
        subprocess.run(
            [
                "git",
                "-c", "protocol.file.allow=never",
                "-c", "protocol.ext.allow=never",
                "clone",
                "--depth", "1",
                "--no-recurse-submodules",
                "--",
                project.repository_url,
                str(workspace),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError:
        shutil.rmtree(workspace, ignore_errors=True)
        raise ValueError("Unable to clone GitHub repository.") from None
    except subprocess.TimeoutExpired:
        shutil.rmtree(workspace, ignore_errors=True)
        raise ValueError("Repository clone timed out.") from None
    except OSError:
        shutil.rmtree(workspace, ignore_errors=True)
        raise ValueError("Unable to prepare repository workspace.") from None

    return str(workspace)
