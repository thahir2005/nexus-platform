from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.environment import Environment
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.project import Project
from app.services.build_pipeline import run_build_pipeline
from app.services.build_preparation import prepare_build_context
from app.services.gitops_publisher import GitOpsPublisher
from app.services.kubernetes_deployer import deploy_application
from app.services.kubernetes_deployer import (
    deploy_application,
    load_local_image_into_minikube,
)


@dataclass
class DeploymentPipelineResult:
    status: str
    project_id: int
    environment_id: int
    image_name: str
    build_id: int
    security_scan_id: int | None
    deployment_id: int | None
    deployment_name: str | None
    service_name: str | None
    namespace: str
    replicas: int
    build_status: str
    validation_status: str
    security_status: str
    high_count: int
    critical_count: int
    message: str


def run_deployment_pipeline(
    db: Session,
    project_id: int,
    environment_id: int,
    repository_path: str,
    image_name: str,
    application_name: str,
    namespace: str = "nexus",
    replicas: int = 1,
) -> DeploymentPipelineResult:

    prepare_build_context(repository_path)

    build_result = run_build_pipeline(
        db=db,
        project_id=project_id,
        repository_path=repository_path,
        image_name=image_name,
    )

    if build_result.status != "success":
        pipeline_run = DeploymentPipelineRun(
            project_id=project_id,
            environment_id=environment_id,
            repository_path=repository_path,
            image_name=image_name,
            application_name=application_name,
            namespace=namespace,
            replicas=replicas,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            status="blocked",
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=f"Deployment blocked: {build_result.message}",
        )

        db.add(pipeline_run)
        db.commit()

        return DeploymentPipelineResult(
            status="blocked",
            project_id=project_id,
            environment_id=environment_id,
            image_name=image_name,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            deployment_name=None,
            service_name=None,
            namespace=namespace,
            replicas=replicas,
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=f"Deployment blocked: {build_result.message}",
        )

    project = db.get(Project, project_id)
    environment = db.get(Environment, environment_id)

    if project is None or environment is None:
        raise ValueError("Project or environment not found")

    # GitOps deployment mode.
    if settings.gitops_enabled:
        try:
            load_local_image_into_minikube(image_name)
            gitops_result = GitOpsPublisher().publish(
                project_name=project.name,
                environment_name=environment.name,
                application_name=application_name,
                image_name=image_name,
                namespace=namespace,
                replicas=replicas,
                build_id=build_result.build_id,
            )
        except Exception as exc:
            gitops_result = None
            gitops_error = str(exc)
        else:
            gitops_error = gitops_result.message

        if gitops_result is None or gitops_result.status == "failed":
            pipeline_run = DeploymentPipelineRun(
                project_id=project_id,
                environment_id=environment_id,
                repository_path=repository_path,
                image_name=image_name,
                application_name=application_name,
                namespace=namespace,
                replicas=replicas,
                build_id=build_result.build_id,
                security_scan_id=build_result.security_scan_id,
                deployment_id=None,
                status="failed",
                build_status=build_result.build_status,
                validation_status=build_result.validation_status,
                security_status=build_result.security_status,
                high_count=build_result.high_count,
                critical_count=build_result.critical_count,
                message=f"GitOps deployment failed: {gitops_error}",
            )

            db.add(pipeline_run)
            db.commit()

            return DeploymentPipelineResult(
                status="failed",
                project_id=project_id,
                environment_id=environment_id,
                image_name=image_name,
                build_id=build_result.build_id,
                security_scan_id=build_result.security_scan_id,
                deployment_id=None,
                deployment_name=None,
                service_name=None,
                namespace=namespace,
                replicas=replicas,
                build_status=build_result.build_status,
                validation_status=build_result.validation_status,
                security_status=build_result.security_status,
                high_count=build_result.high_count,
                critical_count=build_result.critical_count,
                message=f"GitOps deployment failed: {gitops_error}",
            )

        pipeline_run = DeploymentPipelineRun(
            project_id=project_id,
            environment_id=environment_id,
            repository_path=repository_path,
            image_name=image_name,
            application_name=application_name,
            namespace=namespace,
            replicas=replicas,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            status="gitops_pending",
            gitops_revision=gitops_result.revision,
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=(
                f"GitOps published: {gitops_result.message}; "
                f"revision={gitops_result.revision}"
            ),
        )

        db.add(pipeline_run)
        db.commit()

        return DeploymentPipelineResult(
            status="gitops_pending",
            project_id=project_id,
            environment_id=environment_id,
            image_name=image_name,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            deployment_name=application_name,
            service_name=application_name,
            namespace=namespace,
            replicas=replicas,
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=(
                f"GitOps published successfully; "
                f"Argo CD will reconcile revision "
                f"{gitops_result.revision}"
            ),
        )

    # Existing direct Kubernetes deployment mode.
    try:
        deployment_result = deploy_application(
            image_name=image_name,
            application_name=application_name,
            namespace=namespace,
            replicas=replicas,
        )
    except ValueError as exc:
        pipeline_run = DeploymentPipelineRun(
            project_id=project_id,
            environment_id=environment_id,
            repository_path=repository_path,
            image_name=image_name,
            application_name=application_name,
            namespace=namespace,
            replicas=replicas,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            status="failed",
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=f"Deployment failed: {exc}",
        )

        db.add(pipeline_run)
        db.commit()

        return DeploymentPipelineResult(
            status="failed",
            project_id=project_id,
            environment_id=environment_id,
            image_name=image_name,
            build_id=build_result.build_id,
            security_scan_id=build_result.security_scan_id,
            deployment_id=None,
            deployment_name=None,
            service_name=None,
            namespace=namespace,
            replicas=replicas,
            build_status=build_result.build_status,
            validation_status=build_result.validation_status,
            security_status=build_result.security_status,
            high_count=build_result.high_count,
            critical_count=build_result.critical_count,
            message=f"Deployment failed: {exc}",
        )

    deployment = KubernetesDeployment(
        project_id=project_id,
        environment_id=environment_id,
        image_name=image_name,
        application_name=deployment_result.deployment_name,
        namespace=deployment_result.namespace,
        replicas=replicas,
        status=deployment_result.status,
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    pipeline_run = DeploymentPipelineRun(
        project_id=project_id,
        environment_id=environment_id,
        repository_path=repository_path,
        image_name=image_name,
        application_name=application_name,
        namespace=namespace,
        replicas=replicas,
        build_id=build_result.build_id,
        security_scan_id=build_result.security_scan_id,
        deployment_id=deployment.id,
        status="deployed",
        build_status=build_result.build_status,
        validation_status=build_result.validation_status,
        security_status=build_result.security_status,
        high_count=build_result.high_count,
        critical_count=build_result.critical_count,
        message=deployment_result.message,
    )

    db.add(pipeline_run)
    db.commit()

    return DeploymentPipelineResult(
        status="deployed",
        project_id=project_id,
        environment_id=environment_id,
        image_name=image_name,
        build_id=build_result.build_id,
        security_scan_id=build_result.security_scan_id,
        deployment_id=deployment.id,
        deployment_name=deployment_result.deployment_name,
        service_name=deployment_result.service_name,
        namespace=namespace,
        replicas=replicas,
        build_status=build_result.build_status,
        validation_status=build_result.validation_status,
        security_status=build_result.security_status,
        high_count=build_result.high_count,
        critical_count=build_result.critical_count,
        message=deployment_result.message,
    )
