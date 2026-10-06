from dataclasses import dataclass

from app.services.repository_analyzer import RepositoryAnalysis


@dataclass
class DeploymentBlueprint:
    application_type: str
    build_strategy: str
    containerization: str
    ci_cd: str
    kubernetes: str
    helm: str
    recommended_environment: str
    deployment_mode: str


def generate_blueprint(
    analysis: RepositoryAnalysis,
) -> DeploymentBlueprint:

    # Determine application type
    if "Python" in analysis.languages:
        application_type = "Python"
    elif "TypeScript" in analysis.languages:
        application_type = "TypeScript"
    elif "JavaScript" in analysis.languages:
        application_type = "JavaScript"
    elif "Go" in analysis.languages:
        application_type = "Go"
    elif "Java" in analysis.languages:
        application_type = "Java"
    else:
        application_type = "Unknown"

    # Determine build strategy
    if analysis.has_dockerfile:
        build_strategy = "Existing Dockerfile"
    elif application_type == "Python":
        build_strategy = "Python application containerization"
    elif application_type in {"JavaScript", "TypeScript"}:
        build_strategy = "Node.js application containerization"
    else:
        build_strategy = "Containerization required"

    # Containerization
    if analysis.has_dockerfile:
        containerization = "ready"
    else:
        containerization = "recommended"

    # CI/CD
    if analysis.has_ci:
        ci_cd = "detected"
    else:
        ci_cd = "recommended"

    # Kubernetes
    if analysis.has_kubernetes:
        kubernetes = "ready"
    else:
        kubernetes = "recommended"

    # Helm
    if analysis.has_helm:
        helm = "detected"
    else:
        helm = "recommended"

    return DeploymentBlueprint(
        application_type=application_type,
        build_strategy=build_strategy,
        containerization=containerization,
        ci_cd=ci_cd,
        kubernetes=kubernetes,
        helm=helm,
        recommended_environment="development",
        deployment_mode="containerized",
    )