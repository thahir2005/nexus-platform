from fastapi import FastAPI
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

app = FastAPI(
    title="NEXUS Platform API",
    description="Student Developer Platform Control Plane",
    version="0.1.0",
)

app.include_router(
    projects_router,
    prefix="/api/v1",
)

app.include_router(
    environments_router,
    prefix="/api/v1",
)

app.include_router(
    deployments_router,
    prefix="/api/v1",
)

app.include_router(
    github_router,
    prefix="/api/v1",
)

app.include_router(
    repository_router,
    prefix="/api/v1",
)

app.include_router(
    blueprint_router,
    prefix="/api/v1",
)

app.include_router(
    build_plan_router,
    prefix="/api/v1",
)

app.include_router(
    docker_build_router,
    prefix="/api/v1",
)

app.include_router(
    docker_validation_router,
    prefix="/api/v1",
)

app.include_router(
    build_pipeline_router,
    prefix="/api/v1",
)

app.include_router(builds.router, prefix="/api/v1")


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