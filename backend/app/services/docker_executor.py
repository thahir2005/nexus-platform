from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class DockerBuildResult:
    status: str
    image_name: str
    output: str


def build_image(
    repository_path: str,
    image_name: str,
) -> DockerBuildResult:
    path = Path(repository_path)

    if not path.exists():
        raise ValueError("Repository path does not exist")

    if not path.is_dir():
        raise ValueError("Repository path must be a directory")

    dockerfile = path / "Dockerfile"

    if not dockerfile.exists():
        raise ValueError("Dockerfile not found in repository")

    command = [
        "docker",
        "build",
        "-t",
        image_name,
        str(path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Docker build timed out") from exc

    output = (result.stdout + "\n" + result.stderr).strip()

    if result.returncode != 0:
        return DockerBuildResult(
            status="failed",
            image_name=image_name,
            output=output,
        )

    return DockerBuildResult(
        status="success",
        image_name=image_name,
        output=output,
    )