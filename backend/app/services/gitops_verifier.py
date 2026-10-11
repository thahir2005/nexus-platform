from pathlib import Path
from typing import Any

import httpx
import yaml

from app.core.config import settings


class GitOpsVerifier:
    """Verify GitOps revision ancestry and the expected Deployment manifest."""

    @staticmethod
    def _valid_revision(revision: str | None) -> bool:
        return (
            isinstance(revision, str)
            and len(revision) in (40, 64)
            and all(
                char in "0123456789abcdefABCDEF"
                for char in revision
            )
        )

    @staticmethod
    def _slug(value: str) -> str:
        result = "".join(
            char.lower() if char.isalnum() else "-"
            for char in value
        )

        while "--" in result:
            result = result.replace("--", "-")

        return result.strip("-") or "app"

    @staticmethod
    def _failure(message: str) -> dict[str, Any]:
        return {"verified": False, "message": message}

    def verify_deployment(
        self,
        revision: str | None,
        project_name: str,
        environment_name: str,
        application_name: str,
        namespace: str,
        build_id: int,
        published_revision: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> dict[str, Any]:
        if not self._valid_revision(revision):
            return self._failure("Applied Git revision is missing or invalid")

        if not self._valid_revision(published_revision):
            return self._failure(
                "Published Git revision is missing or invalid"
            )

        repository = settings.gitops_repo_url.removesuffix(".git")

        if not repository.startswith("https://github.com/"):
            return self._failure("Unsupported GitOps repository URL")

        owner_repo = repository.removeprefix("https://github.com/")
        parts = owner_repo.split("/")

        if (
            len(parts) != 2
            or any(not part for part in parts)
            or any(char in owner_repo for char in "?#")
        ):
            return self._failure("Invalid GitHub repository URL")

        relative_manifest = (
            Path(settings.gitops_root_path)
            / self._slug(project_name)
            / self._slug(environment_name)
            / "application.yaml"
        )

        if (
            relative_manifest.is_absolute()
            or ".." in relative_manifest.parts
        ):
            return self._failure("Invalid GitOps manifest path")

        compare_url = (
            f"https://api.github.com/repos/{owner_repo}/compare/"
            f"{published_revision}...{revision}"
        )

        manifest_url = (
            f"https://raw.githubusercontent.com/{owner_repo}/"
            f"{revision}/{relative_manifest.as_posix()}"
        )

        try:
            comparison_response = httpx.get(
                compare_url,
                timeout=timeout_seconds,
                headers={"Accept": "application/vnd.github+json"},
            )
            comparison_response.raise_for_status()
            comparison = comparison_response.json()

            if comparison.get("status") not in ("ahead", "identical"):
                return self._failure(
                    "Applied revision does not descend from the published revision"
                )

            manifest_response = httpx.get(
                manifest_url,
                timeout=timeout_seconds,
            )
            manifest_response.raise_for_status()

            for document in yaml.safe_load_all(manifest_response.text):
                if not isinstance(document, dict):
                    continue

                metadata = document.get("metadata") or {}

                if (
                    document.get("kind") != "Deployment"
                    or metadata.get("name") != application_name
                    or metadata.get("namespace") != namespace
                ):
                    continue

                annotations = metadata.get("annotations") or {}
                template_annotations = (
                    (document.get("spec") or {})
                    .get("template", {})
                    .get("metadata", {})
                    .get("annotations")
                    or {}
                )

                expected_build = str(build_id)

                if (
                    annotations.get("nexus.io/build-id") == expected_build
                    and template_annotations.get("nexus.io/build-id")
                    == expected_build
                ):
                    return {
                        "verified": True,
                        "message": (
                            "Revision ancestry and Deployment build verified"
                        ),
                    }

                return self._failure(
                    "GitOps manifest build ID does not match"
                )

            return self._failure("Expected Deployment was not found")

        except (
            httpx.HTTPError,
            yaml.YAMLError,
            ValueError,
        ) as exc:
            return self._failure(
                f"Unable to verify GitOps deployment: {exc}"
            )
