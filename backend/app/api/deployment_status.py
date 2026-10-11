from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.project import Project
from app.schemas.deployment_status import (
    ArgoCDStatus,
    DeploymentPipelineStatus,
    DeploymentStatusResponse,
    GitOpsStatus,
    KubernetesStatus,
    ApplicationHealthStatus,
)
from app.services.application_health import check_application_health
from app.services.argo_cd import ArgoCDService
from app.services.kubernetes_deployer import get_deployment_status
from app.services.gitops_verifier import GitOpsVerifier


router = APIRouter(
    prefix="/api/v1",
    tags=["deployment status"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/projects/{project_id}/deployment-status",
    response_model=DeploymentStatusResponse,
)
def get_deployment_status_summary(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    pipeline = (
        db.query(DeploymentPipelineRun)
        .filter(DeploymentPipelineRun.project_id == project_id)
        .order_by(DeploymentPipelineRun.created_at.desc())
        .first()
    )

    if pipeline is None:
        raise HTTPException(
            status_code=404,
            detail="No deployment pipeline found",
        )

    try:
        kubernetes = get_deployment_status(
            application_name=pipeline.application_name,
            namespace=pipeline.namespace,
        )
    except ValueError as exc:
        if "deployment not found" in str(exc).lower():
            kubernetes = {
                "status": "pending",
                "desired_replicas": getattr(pipeline, "replicas", None) or 1,
                "ready_replicas": 0,
                "available_replicas": 0,
                "deployed_build_id": None,
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Unable to verify Kubernetes deployment status",
            ) from exc

    if pipeline.status == "gitops_pending":
        gitops_status = (
            "published"
            if pipeline.gitops_revision
            else "publication_recorded_revision_unavailable"
        )
    else:
        gitops_status = "not_used"

    argo_status = ArgoCDService().get_status()

    application_health = check_application_health(
        settings.application_health_url,
        timeout_seconds=settings.application_health_timeout_seconds,
    )

    if argo_status["status"] != "available":
        deployment_state = "unavailable"

    elif argo_status["sync_status"] == "OutOfSync":
        deployment_state = "reconciling"

    elif (
        kubernetes["status"] != "running"
        or kubernetes["desired_replicas"] <= 0
        or kubernetes["ready_replicas"] != kubernetes["desired_replicas"]
        or kubernetes["available_replicas"] != kubernetes["desired_replicas"]
        or kubernetes["deployed_build_id"] != pipeline.build_id
        or application_health["status"] != "healthy"
    ):
        deployment_state = "pending"

    elif pipeline.status == "gitops_pending" and (
        not pipeline.gitops_revision
        or not GitOpsVerifier().verify_deployment(
            revision=argo_status.get("applied_revision"),
            published_revision=pipeline.gitops_revision,
            project_name=project.name,
            environment_name=pipeline.environment.name,
            application_name=pipeline.application_name,
            namespace=pipeline.namespace,
            build_id=pipeline.build_id,
        )["verified"]
    ):
        deployment_state = "reconciling"

    elif (
        argo_status["sync_status"] == "Synced"
        and argo_status["health_status"] == "Healthy"
    ):
        deployment_state = "deployed"

    else:
        deployment_state = "pending"

    return DeploymentStatusResponse(
        project_id=project_id,
        application_url=settings.application_url,
        deployment_state=deployment_state,
        environment_id=pipeline.environment_id,
        environment_name=pipeline.environment.name,
        image_name=pipeline.image_name,
        application_name=pipeline.application_name,
        pipeline=DeploymentPipelineStatus(
            id=pipeline.id,
            status=pipeline.status,
            build_id=pipeline.build_id,
            security_scan_id=pipeline.security_scan_id,
            build_status=pipeline.build_status,
            validation_status=pipeline.validation_status,
            security_status=pipeline.security_status,
            high_count=pipeline.high_count,
            critical_count=pipeline.critical_count,
            message=pipeline.message,
            created_at=pipeline.created_at,
        ),
        gitops=GitOpsStatus(
            status=gitops_status,
            revision=pipeline.gitops_revision,
        ),

        argo=ArgoCDStatus(
            status=argo_status["status"],
            application_name=argo_status["application_name"],
            sync_status=argo_status["sync_status"],
            health_status=argo_status["health_status"],
            revision=argo_status["revision"],
            operation_phase=argo_status["operation_phase"],
            operation_message=argo_status["operation_message"],
        ),
        kubernetes=KubernetesStatus(
            status=kubernetes["status"],
            deployment_name=pipeline.application_name,
            namespace=pipeline.namespace,
            desired_replicas=kubernetes["desired_replicas"],
            ready_replicas=kubernetes["ready_replicas"],
            available_replicas=kubernetes["available_replicas"],
        ),
        application_health=ApplicationHealthStatus(**application_health),
    )
