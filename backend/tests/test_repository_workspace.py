from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.models.project import Project
from app.services import repository_workspace


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://github.com.evil.example/owner/repo",
        "https://user:password@github.com/owner/repo",
        "https://github.com:8443/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo?redirect=example",
        "https://github.com/owner/repo#fragment",
    ],
)
def test_rejects_unsafe_github_urls(url):
    with pytest.raises(ValueError):
        repository_workspace._validate_github_url(url)


def test_accepts_canonical_github_urls():
    repository_workspace._validate_github_url(
        "https://github.com/example/project"
    )
    repository_workspace._validate_github_url(
        "https://github.com/example/project.git"
    )


def test_workspace_clone_uses_unique_directory(tmp_path):
    project = Project(
        id=12345,
        name="workspace-test",
        repository_url="https://github.com/example/project",
        owner_id=1,
    )

    with (
        patch.object(repository_workspace, "WORKSPACE_ROOT", tmp_path),
        patch.object(repository_workspace.subprocess, "run") as mock_run,
    ):
        mock_run.return_value.returncode = 0

        first = repository_workspace.prepare_repository_workspace(project)
        second = repository_workspace.prepare_repository_workspace(project)

    assert first != second
    assert Path(first).parent == tmp_path
    assert Path(second).parent == tmp_path
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].kwargs["timeout"] == 120


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo%2Fother",
        "https://github.com/owner/../repo",
        "https://github.com/owner/repo/",
        "https://github.com//repo",
        "https://github.com/owner/repo\\other",
        "https://github.com/owner/repo\n",
        "https://github.com:443/owner/repo",
    ],
)
def test_rejects_noncanonical_repository_urls(url):
    with pytest.raises(ValueError):
        repository_workspace._validate_github_url(url)


def test_failed_clone_removes_partial_workspace(tmp_path):
    project = Project(
        id=12346,
        name="workspace-failure-test",
        repository_url="https://github.com/example/project",
        owner_id=1,
    )

    def fail_clone(*args, **kwargs):
        destination = Path(args[0][args[0].index("--") + 2])
        destination.mkdir()
        (destination / "partial-file").write_text("partial")
        raise repository_workspace.subprocess.CalledProcessError(
            128, args[0]
        )

    with (
        patch.object(repository_workspace, "WORKSPACE_ROOT", tmp_path),
        patch.object(
            repository_workspace.subprocess,
            "run",
            side_effect=fail_clone,
        ),
    ):
        with pytest.raises(ValueError, match="Unable to clone"):
            repository_workspace.prepare_repository_workspace(project)

    assert list(tmp_path.iterdir()) == []
