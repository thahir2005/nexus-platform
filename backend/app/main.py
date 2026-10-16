from fastapi import Depends, FastAPI
from app.core.auth import require_request_access
from app.api.projects import router as projects_router
from app.api.environments import router as environments_router
from app.api.deployments import router as deployments_router
from app.api.github import router as github_router
from app.api.repository import router as repository_router
from app.api.blueprint import router as blueprint_router
from app.api.build_plan import router as build_plan_router
from app.api.docker_build import router as docker_build_router
from app.api.docker_validation import router as docker_validation_router
from app.api.build_pipeline import router as build_pipeline_router
from app.api import builds
from app.api import security_scans
from app.api import kubernetes
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.deployment_pipeline import router as deployment_pipeline_router
from app.api import deployment_history
from app.api import deployment_status

app = FastAPI(
    title="NEXUS Platform API",
    description="Student Developer Platform Control Plane",
    version="0.1.0",
)
Instrumentator().instrument(app).expose(app)


def include_protected(router, **kwargs):
    """Mount API routers behind session authentication and project ownership."""
    app.include_router(
        router, dependencies=[Depends(require_request_access)], **kwargs
    )

include_protected(
    projects_router,
    prefix="/api/v1",
)

include_protected(
    environments_router,
    prefix="/api/v1",
)

include_protected(
    deployments_router,
    prefix="/api/v1",
)

include_protected(
    github_router,
    prefix="/api/v1",
)

include_protected(
    repository_router,
    prefix="/api/v1",
)

include_protected(
    blueprint_router,
    prefix="/api/v1",
)

include_protected(
    build_plan_router,
    prefix="/api/v1",
)

include_protected(
    docker_build_router,
    prefix="/api/v1",
)

include_protected(
    docker_validation_router,
    prefix="/api/v1",
)

include_protected(
    build_pipeline_router,
    prefix="/api/v1",
)

include_protected(builds.router, prefix="/api/v1")

include_protected(security_scans.router)

include_protected(kubernetes.router)

include_protected(deployment_pipeline_router)

include_protected(deployment_history.router)

include_protected(deployment_status.router)


@app.get("/")
async def root():
    return {
        "name": "NEXUS",
        "description": "Student Developer Platform",
        "version": "0.1.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "nexus-api",
    }


@app.get("/api/v1/platform")
async def platform_info():
    return {
        "platform": "NEXUS",
        "environment": "development",
        "capabilities": [
            "project-management",
            "deployment-management",
            "environment-management",
        ],
    }