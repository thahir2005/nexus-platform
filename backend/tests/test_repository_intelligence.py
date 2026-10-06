from app.services.blueprint import generate_blueprint
from app.services.repository_analyzer import analyze_repository


def test_python_repository_detection():
    analysis = analyze_repository(
        [
            "app/main.py",
            "requirements.txt",
            "tests/test_main.py",
            "README.md",
        ]
    )

    assert "Python" in analysis.languages
    assert analysis.has_tests is True
    assert analysis.has_readme is True
    assert analysis.has_dockerfile is False
    assert analysis.has_ci is False


def test_devops_repository_detection():
    analysis = analyze_repository(
        [
            "app/main.py",
            "Dockerfile",
            ".github/workflows/ci.yml",
            "k8s/deployment.yaml",
            "charts/nexus/Chart.yaml",
            "tests/test_main.py",
            "README.md",
        ]
    )

    assert "Python" in analysis.languages
    assert analysis.has_dockerfile is True
    assert analysis.has_ci is True
    assert analysis.has_kubernetes is True
    assert analysis.has_helm is True
    assert analysis.has_tests is True
    assert analysis.has_readme is True


def test_javascript_repository_detection():
    analysis = analyze_repository(
        [
            "src/App.jsx",
            "package.json",
            "README.md",
        ]
    )

    assert "JavaScript" in analysis.languages
    assert analysis.has_readme is True


def test_blueprint_for_python_without_docker():
    analysis = analyze_repository(
        [
            "app/main.py",
            "requirements.txt",
            "tests/test_main.py",
        ]
    )

    blueprint = generate_blueprint(analysis)

    assert blueprint.application_type == "Python"
    assert blueprint.containerization == "recommended"
    assert blueprint.ci_cd == "recommended"
    assert blueprint.kubernetes == "recommended"
    assert blueprint.helm == "recommended"
    assert blueprint.deployment_mode == "containerized"


def test_blueprint_for_existing_devops_setup():
    analysis = analyze_repository(
        [
            "app/main.py",
            "Dockerfile",
            ".github/workflows/ci.yml",
            "k8s/deployment.yaml",
            "charts/nexus/Chart.yaml",
        ]
    )

    blueprint = generate_blueprint(analysis)

    assert blueprint.application_type == "Python"
    assert blueprint.containerization == "ready"
    assert blueprint.ci_cd == "detected"
    assert blueprint.kubernetes == "ready"
    assert blueprint.helm == "detected"