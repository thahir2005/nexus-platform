from dataclasses import dataclass

from app.services.blueprint import DeploymentBlueprint


@dataclass
class BuildPlan:
    build_type: str
    dockerfile_required: bool
    image_name: str
    target_environment: str
    steps: list[str]


def generate_build_plan(
    blueprint: DeploymentBlueprint,
    project_name: str,
) -> BuildPlan:
    if blueprint.deployment_mode != "containerized":
        raise ValueError(
            "NEXUS currently supports containerized deployments only"
        )

    image_name = (
        f"nexus/{project_name.lower().replace('_', '-').replace(' ', '-')}"
    )

    if blueprint.containerization == "ready":
        dockerfile_required = False
        first_step = "Use existing Dockerfile"
    else:
        dockerfile_required = True
        first_step = "Generate Dockerfile"

    steps = [
        first_step,
        "Build Docker image",
        "Validate image",
        "Deploy to development environment",
    ]

    return BuildPlan(
        build_type="docker",
        dockerfile_required=dockerfile_required,
        image_name=image_name,
        target_environment=blueprint.recommended_environment,
        steps=steps,
    )