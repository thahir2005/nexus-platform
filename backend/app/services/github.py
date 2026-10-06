import httpx


class GitHubService:
    API_BASE_URL = "https://api.github.com"

    def parse_repository_url(self, repository_url: str) -> tuple[str, str]:
        cleaned = repository_url.strip().rstrip("/")
        prefix = "https://github.com/"

        if not cleaned.startswith(prefix):
            raise ValueError(
                "Only public GitHub repository URLs are supported"
            )

        path = cleaned[len(prefix):]
        parts = path.split("/")

        if len(parts) != 2 or not all(parts):
            raise ValueError("Invalid GitHub repository URL")

        owner, repository = parts

        if repository.endswith(".git"):
            repository = repository[:-4]

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