from dataclasses import dataclass
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings


@dataclass
class GitOpsPublishResult:
    status: str
    revision: str | None
    manifest_path: str
    message: str


class GitOpsPublisher:
    @staticmethod
    def _run(
        command: list[str],
        cwd: Path | None = None,
    ) -> str:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

        return result.stdout.strip()

    @staticmethod
    def _slug(value: str) -> str:
        result = "".join(
            char.lower() if char.isalnum() else "-"
            for char in value
        )

        while "--" in result:
            result = result.replace("--", "-")

        return result.strip("-") or "app"

    def publish(
        self,
        project_name: str,
        environment_name: str,
        application_name: str,
        image_name: str,
        namespace: str,
        replicas: int,
        build_id: int,
    ) -> GitOpsPublishResult:
        project_slug = self._slug(project_name)
        environment_slug = self._slug(environment_name)

        relative_manifest = (
            Path(settings.gitops_root_path)
            / project_slug
            / environment_slug
            / "application.yaml"
        )

        workdir = Path(
            tempfile.mkdtemp(prefix="nexus-gitops-")
        )

        try:
            self._run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    settings.gitops_branch,
                    settings.gitops_repo_url,
                    str(workdir),
                ]
            )

            manifest_path = workdir / relative_manifest
            manifest_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            deployment = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {application_name}
  namespace: {namespace}
  labels:
    app: {application_name}
  annotations:
    nexus.io/build-id: "{build_id}"
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {application_name}
  template:
    metadata:
      labels:
        app: {application_name}
      annotations:
        nexus.io/build-id: "{build_id}"
    spec:
      containers:
        - name: app
          image: {image_name}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: {application_name}
  namespace: {namespace}
spec:
  selector:
    app: {application_name}
  ports:
    - port: 8000
      targetPort: 8000
"""

            manifest_path.write_text(deployment)

            self._run(
                ["git", "add", str(relative_manifest)],
                cwd=workdir,
            )

            diff = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=workdir,
            )

            if diff.returncode == 0:
                return GitOpsPublishResult(
                    status="unchanged",
                    revision=None,
                    manifest_path=str(relative_manifest),
                    message=(
                        "GitOps manifest already matches desired state"
                    ),
                )

            self._run(
                ["git", "config", "user.name", "NEXUS Platform"],
                cwd=workdir,
            )

            self._run(
                ["git", "config", "user.email", "nexus@localhost"],
                cwd=workdir,
            )

            self._run(
                [
                    "git",
                    "commit",
                    "-m",
                    (
                        f"chore: deploy {application_name} "
                        f"build {build_id}"
                    ),
                ],
                cwd=workdir,
            )

            if settings.gitops_push:
                self._run(
                    [
                        "git",
                        "push",
                        "origin",
                        settings.gitops_branch,
                    ],
                    cwd=workdir,
                )

            revision = self._run(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
            )

            return GitOpsPublishResult(
                status="published",
                revision=revision,
                manifest_path=str(relative_manifest),
                message=(
                    "GitOps manifest committed and pushed successfully"
                ),
            )

        except subprocess.CalledProcessError as exc:
            output = (
                exc.stderr.strip()
                or exc.stdout.strip()
                or str(exc)
            )

            return GitOpsPublishResult(
                status="failed",
                revision=None,
                manifest_path=str(relative_manifest),
                message=f"GitOps publish failed: {output}",
            )

        finally:
            shutil.rmtree(workdir, ignore_errors=True)
