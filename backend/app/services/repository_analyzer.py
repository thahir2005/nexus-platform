from dataclasses import dataclass


@dataclass
class RepositoryAnalysis:
    languages: list[str]
    frameworks: list[str]
    has_dockerfile: bool
    has_ci: bool
    has_kubernetes: bool
    has_helm: bool
    has_tests: bool
    has_readme: bool


def analyze_repository(paths: list[str]) -> RepositoryAnalysis:
    normalized = {path.lower() for path in paths}

    languages: set[str] = set()
    frameworks: set[str] = set()

    if any(path.endswith(".py") for path in normalized):
        languages.add("Python")

    if any(
        path.endswith(".js") or path.endswith(".jsx")
        for path in normalized
    ):
        languages.add("JavaScript")

    if any(
        path.endswith(".ts") or path.endswith(".tsx")
        for path in normalized
    ):
        languages.add("TypeScript")

    if any(path.endswith(".go") for path in normalized):
        languages.add("Go")

    if any(path.endswith(".java") for path in normalized):
        languages.add("Java")

    if "requirements.txt" in normalized:
        frameworks.add("Python ecosystem")

    if "pyproject.toml" in normalized:
        frameworks.add("Python ecosystem")

    if "package.json" in normalized:
        frameworks.add("Node.js ecosystem")

    if "manage.py" in normalized:
        frameworks.add("Django")

    if any(
        path in {"requirements.txt", "pyproject.toml", "poetry.lock"}
        for path in normalized
    ):
        pass

    has_dockerfile = any(
        path == "dockerfile" or path.endswith("/dockerfile")
        for path in normalized
    )

    has_ci = any(
        path.startswith(".github/workflows/")
        for path in normalized
    )

    has_kubernetes = any(
        "kubernetes" in path
        or path.startswith("k8s/")
        or path.startswith("kubernetes/")
        or path.endswith(".yaml")
        and (
            "deployment" in path
            or "service" in path
        )
        for path in normalized
    )

    has_helm = any(
        path.startswith("charts/")
        or "/templates/" in path
        or path.endswith("chart.yaml")
        for path in normalized
    )

    has_tests = any(
        "test" in path
        for path in normalized
    )

    has_readme = any(
        path in {"readme.md", "readme"}
        for path in normalized
    )

    return RepositoryAnalysis(
        languages=sorted(languages),
        frameworks=sorted(frameworks),
        has_dockerfile=has_dockerfile,
        has_ci=has_ci,
        has_kubernetes=has_kubernetes,
        has_helm=has_helm,
        has_tests=has_tests,
        has_readme=has_readme,
    )