from dataclasses import dataclass
import json
import subprocess


@dataclass
class DockerValidationResult:
    status: str
    image_name: str
    image_id: str | None
    architecture: str | None
    os: str | None
    size: str | None
    message: str


def validate_image(image_name: str) -> DockerValidationResult:
    inspect_command = [
        "docker",
        "image",
        "inspect",
        image_name,
    ]

    try:
        result = subprocess.run(
            inspect_command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Docker image validation timed out") from exc

    if result.returncode != 0:
        return DockerValidationResult(
            status="failed",
            image_name=image_name,
            image_id=None,
            architecture=None,
            os=None,
            size=None,
            message="Docker image does not exist",
        )

    try:
        metadata = json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        raise ValueError("Unable to parse Docker image metadata") from exc

    return DockerValidationResult(
        status="valid",
        image_name=image_name,
        image_id=metadata.get("Id"),
        architecture=metadata.get("Architecture"),
        os=metadata.get("Os"),
        size=str(metadata.get("Size")),
        message="Docker image exists and metadata is valid",
    )