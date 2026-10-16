import re
from urllib.parse import urlsplit

import httpx


_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class GitHubService:
    API_BASE_URL = "https://api.github.com"

    def parse_repository_url(self, repository_url: str) -> tuple[str, str]:
        if not isinstance(repository_url, str) or not repository_url:
            raise ValueError("A valid GitHub repository URL is required")

        if repository_url != repository_url.strip():
            raise ValueError("Invalid GitHub repository URL")

        if any(ord(char) < 32 or char.isspace() for char in repository_url):
            raise ValueError("Invalid GitHub repository URL")

        if "%" in repository_url or "\\" in repository_url:
            raise ValueError("Invalid GitHub repository URL")

        try:
            parsed = urlsplit(repository_url)
            port = parsed.port
        except ValueError:
            raise ValueError("Invalid GitHub repository URL") from None

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
            raise ValueError(
                "Only canonical public GitHub repository URLs are supported"
            )

        parts = parsed.path.split("/")

        if len(parts) != 3 or parts[0] != "" or not parts[1] or not parts[2]:
            raise ValueError("Invalid GitHub repository URL")

        owner, repository = parts[1], parts[2]

        if repository.endswith(".git"):
            repository = repository[:-4]

        if (
            not _OWNER_PATTERN.fullmatch(owner)
            or not _REPOSITORY_PATTERN.fullmatch(repository)
            or repository in {".", ".."}
            or repository.endswith(".")
        ):
            raise ValueError("Invalid GitHub repository URL")

        return owner, repository

    async def get_repository(self, repository_url: str) -> dict:
        owner, repository = self.parse_repository_url(repository_url)

        url = f"{self.API_BASE_URL}/repos/{owner}/{repository}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Accept": "application/vnd.github+json"},
            )

        if response.status_code == 404:
            raise ValueError("GitHub repository not found")

        if response.status_code != 200:
            raise ValueError(
                f"GitHub API returned status {response.status_code}"
            )

        data = response.json()

        return {
            "name": data["name"],
            "description": data.get("description"),
            "repository_url": data["html_url"],
            "default_branch": data.get("default_branch"),
            "language": data.get("language"),
            "visibility": data.get("visibility"),
        }

    async def get_repository_tree(
        self,
        repository_url: str,
        default_branch: str,
    ) -> list[str]:
        owner, repository = self.parse_repository_url(repository_url)

        url = (
            f"{self.API_BASE_URL}/repos/"
            f"{owner}/{repository}/git/trees/"
            f"{default_branch}?recursive=1"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers={"Accept": "application/vnd.github+json"},
            )

        if response.status_code == 404:
            raise ValueError("GitHub repository tree not found")

        if response.status_code != 200:
            raise ValueError(
                f"GitHub API returned status {response.status_code}"
            )

        data = response.json()

        return [
            item["path"]
            for item in data.get("tree", [])
            if item.get("type") == "blob"
        ]


github_service = GitHubService()
