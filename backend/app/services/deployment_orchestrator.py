from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.deployment_pipeline_run import DeploymentPipelineRun
from app.models.kubernetes_deployment import KubernetesDeployment
from app.services.build_pipeline import run_build_pipeline
from app.services.kubernetes_deployer import deploy_application


@dataclass
class DeploymentPipelineResult:
    status: str
    project_id: int
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
    repository_path: str,
    image_name: str,
    application_name: str,
    namespace: str = "nexus",
    replicas: int = 1,
) -> DeploymentPipelineResult:

    # 1. Build + validation + security gate
    build_result = run_build_pipeline(
        db=db,
        project_id=project_id,
        repository_path=repository_path,
        image_name=image_name,
    )

    # 2. Stop if the pipeline is blocked
    if build_result.status != "success":
        pipeline_run = DeploymentPipelineRun(
            project_id=project_id,
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

    # 3. Deploy only after security gate passes
    deployment_result = deploy_application(
        image_name=image_name,
        application_name=application_name,
        namespace=namespace,
        replicas=replicas,
    )

    # 4. Persist Kubernetes deployment
    deployment = KubernetesDeployment(
        project_id=project_id,
        image_name=image_name,
        application_name=deployment_result.deployment_name,
        namespace=deployment_result.namespace,
        replicas=replicas,
        status=deployment_result.status,
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # 5. Persist pipeline history
    pipeline_run = DeploymentPipelineRun(
        project_id=project_id,
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
        image_name=image_name,
        build_id=build_result.build_id,
        security_scan_id=build_result.security_scan_id,
        deployment_id=deployment.id,
        deployment_name=deployment_result.deployment_name,
        service_name=deployment_result.service_name,
        namespace=deployment_result.namespace,
        replicas=replicas,
        build_status=build_result.build_status,
        validation_status=build_result.validation_status,
        security_status=build_result.security_status,
        high_count=build_result.high_count,
        critical_count=build_result.critical_count,
        message=deployment_result.message,
    )
