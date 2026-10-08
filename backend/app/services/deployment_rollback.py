from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.kubernetes_deployment import KubernetesDeployment
from app.services.kubernetes_deployer import deploy_application


@dataclass
class DeploymentRollbackResult:
    status: str
    project_id: int
    environment_id: int
    deployment_id: int
    rollback_of_id: int
    image_name: str
    deployment_name: str
    service_name: str
    namespace: str
    replicas: int
    message: str


def rollback_deployment(
    db: Session,
    project_id: int,
    deployment_id: int,
) -> DeploymentRollbackResult:

    current = db.get(KubernetesDeployment, deployment_id)

    if current is None or current.project_id != project_id:
        raise ValueError("Deployment not found")

    if current.environment_id is None:
        raise ValueError("Deployment has no environment")

    previous_run = (
        db.query(DeploymentPipelineRun)
        .filter(
            DeploymentPipelineRun.project_id == project_id,
            DeploymentPipelineRun.environment_id == current.environment_id,
            DeploymentPipelineRun.status == "deployed",
            DeploymentPipelineRun.deployment_id.is_not(None),
            DeploymentPipelineRun.deployment_id != deployment_id,
        )
        .order_by(DeploymentPipelineRun.created_at.desc())
        .first()
    )

    if previous_run is None or previous_run.deployment is None:
        raise ValueError(
            "No previous successful deployment is available for rollback"
        )

    target = previous_run.deployment

    result = deploy_application(
        image_name=target.image_name,
        application_name=current.application_name,
        namespace=current.namespace,
        replicas=current.replicas,
    )

    rollback = KubernetesDeployment(
        project_id=project_id,
        environment_id=current.environment_id,
        image_name=target.image_name,
        application_name=result.deployment_name,
        namespace=result.namespace,
        replicas=current.replicas,
        status=result.status,
        rollback_of_id=current.id,
    )

    db.add(rollback)
    db.commit()
    db.refresh(rollback)

    return DeploymentRollbackResult(
        status="rolled_back",
        project_id=project_id,
        environment_id=current.environment_id,
        deployment_id=rollback.id,
        rollback_of_id=current.id,
        image_name=target.image_name,
        deployment_name=result.deployment_name,
        service_name=result.service_name,
        namespace=result.namespace,
        replicas=current.replicas,
        message=(
            f"Rolled back deployment {current.id} to "
            f"previous deployment {target.id}; "
            f"{current.replicas}/{current.replicas} replicas ready"
        ),
    )
