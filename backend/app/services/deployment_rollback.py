from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.environment import Environment
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.project import Project
from app.services.gitops_publisher import GitOpsPublisher
from app.services.kubernetes_deployer import deploy_application, load_local_image_into_minikube


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

    if settings.gitops_enabled:
        project = db.get(Project, project_id)
        environment = db.get(Environment, current.environment_id)

        if project is None or environment is None:
            raise ValueError("Project or environment not found for GitOps rollback")

        load_local_image_into_minikube(target.image_name)

        publish_result = GitOpsPublisher().publish(
            project_name=project.name,
            environment_name=environment.name,
            application_name=current.application_name,
            image_name=target.image_name,
            namespace=current.namespace,
            replicas=current.replicas,
            build_id=previous_run.build_id,
        )

        if publish_result.status == "failed":
            raise ValueError(
                f"GitOps rollback publication failed: {publish_result.message}"
            )

        if publish_result.status not in {"published", "unchanged"}:
            raise ValueError(
                f"Unexpected GitOps rollback status: {publish_result.status}"
            )

        status = "gitops_pending"
        if publish_result.status == "published":
            message = (
                f"Rollback requested to image {target.image_name}. "
                f"GitOps revision: {publish_result.revision or 'not provided'}. "
                "Argo CD must reconcile the change before the rollback is considered deployed."
            )
        else:
            message = (
                f"Rollback requested to image {target.image_name}. "
                "The GitOps manifest already matches the requested state; "
                "verify Argo CD and Kubernetes before considering the rollback deployed."
            )
        service_name = current.application_name
        result_status = status
    else:
        result = deploy_application(
            image_name=target.image_name,
            application_name=current.application_name,
            namespace=current.namespace,
            replicas=current.replicas,
        )
        status = result.status
        message = (
            f"Rolled back deployment {current.id} to "
            f"previous deployment {target.id}; "
            f"{current.replicas}/{current.replicas} replicas requested"
        )
        service_name = result.service_name
        result_status = "rolled_back"

    rollback = KubernetesDeployment(
        project_id=project_id,
        environment_id=current.environment_id,
        image_name=target.image_name,
        application_name=current.application_name,
        namespace=current.namespace,
        replicas=current.replicas,
        status=status,
        rollback_of_id=current.id,
    )

    db.add(rollback)
    db.commit()
    db.refresh(rollback)

    return DeploymentRollbackResult(
        status=result_status,
        project_id=project_id,
        environment_id=current.environment_id,
        deployment_id=rollback.id,
        rollback_of_id=current.id,
        image_name=target.image_name,
        deployment_name=current.application_name,
        service_name=service_name,
        namespace=current.namespace,
        replicas=current.replicas,
        message=message,
    )
