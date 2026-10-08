import json
from pathlib import Path


def prepare_build_context(repository_path: str) -> None:
    root = Path(repository_path)

    if not root.exists():
        raise ValueError("Repository workspace does not exist.")

    # Existing Dockerfile: use it as-is.
    if (root / "Dockerfile").exists():
        return

    package_json = root / "package.json"

    if package_json.exists():
        return _prepare_node_project(root, package_json)

    requirements = root / "requirements.txt"

    if requirements.exists():
        return _prepare_python_project(root, requirements)

    raise ValueError(
        "NEXUS could not determine how to build this repository. "
        "Add a Dockerfile or use a supported application structure."
    )


def _prepare_node_project(root: Path, package_json: Path) -> None:
    try:
        package = json.loads(package_json.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid package.json.") from exc

    scripts = package.get("scripts", {})

    if "start" not in scripts:
        project_name = package.get("name", "Node.js project")

        raise ValueError(
            f"'{project_name}' appears to be a Node.js library or framework "
            "because package.json does not define a start script. "
            "NEXUS only deploys runnable applications."
        )

    dockerfile = """FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev; fi

COPY . .

ENV NODE_ENV=production
ENV PORT=8000

EXPOSE 8000

CMD ["npm", "start"]
"""

    (root / "Dockerfile").write_text(dockerfile)


def _prepare_python_project(root: Path, requirements: Path) -> None:
    if (root / "app" / "main.py").exists():
        module = "app.main:app"
    elif (root / "main.py").exists():
        module = "main:app"
    else:
        raise ValueError(
            "Python repository detected, but NEXUS could not find "
            "app/main.py or main.py with a standard FastAPI application."
        )

    dockerfile = f"""FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "{module}", "--host", "0.0.0.0", "--port", "8000"]
"""

    (root / "Dockerfile").write_text(dockerfile)
