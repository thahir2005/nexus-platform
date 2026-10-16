import pytest

from app.services.github import GitHubService


@pytest.fixture
def service():
    return GitHubService()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/example/project", ("example", "project")),
        ("https://github.com/example/project.git", ("example", "project")),
        ("https://github.com/Example-Org/project_1", ("Example-Org", "project_1")),
        ("https://github.com/example/project.name", ("example", "project.name")),
    ],
)
def test_accepts_valid_github_repository_urls(service, url, expected):
    assert service.parse_repository_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "http://github.com/example/project",
        "https://github.com.evil.example/example/project",
        "https://evil.example/github.com/example/project",
        "https://user:password@github.com/example/project",
        "https://github.com:443/example/project",
        "https://github.com/example/project?redirect=evil",
        "https://github.com/example/project#fragment",
        "https://github.com/example/project/extra",
        "https://github.com/example",
        "https://github.com//project",
        "https://github.com/example/",
        " https://github.com/example/project",
        "https://github.com/example/project ",
        "https://github.com/example%2Fother/project",
        "https://github.com/example/repo with spaces",
        "https://github.com/-invalid/project",
        "https://github.com/example/-invalid",
        "https://github.com/example/project..",
        "https://github.com/example/.",
        "https://github.com/example/..",
        "https://github.com/example/project\\extra",
    ],
)
def test_rejects_invalid_github_repository_urls(service, url):
    with pytest.raises(ValueError):
        service.parse_repository_url(url)
