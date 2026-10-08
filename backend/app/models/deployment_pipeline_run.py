
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class DeploymentPipelineRun(Base):

    __tablename__ = "deployment_pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(

        ForeignKey("projects.id"),

        nullable=False,

        index=True,

    )

    repository_path: Mapped[str] = mapped_column(

        String(500),

        nullable=False,

    )

    image_name: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

    )

    application_name: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

    )

    namespace: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

    )

    replicas: Mapped[int] = mapped_column(

        Integer,

        nullable=False,

    )

    build_id: Mapped[int] = mapped_column(

        ForeignKey("builds.id"),

        nullable=False,

        index=True,

    )

    security_scan_id: Mapped[int | None] = mapped_column(

        ForeignKey("security_scans.id"),

        nullable=True,

        index=True,

    )

    deployment_id: Mapped[int | None] = mapped_column(

        ForeignKey("kubernetes_deployments.id"),

        nullable=True,

        index=True,

    )

    status: Mapped[str] = mapped_column(

        String(50),

        nullable=False,

    )

    build_status: Mapped[str] = mapped_column(

        String(50),

        nullable=False,

    )

    validation_status: Mapped[str] = mapped_column(

        String(50),

        nullable=False,

    )

    security_status: Mapped[str] = mapped_column(

        String(50),

        nullable=False,

    )

    high_count: Mapped[int] = mapped_column(

        Integer,

        nullable=False,

        default=0,

    )

    critical_count: Mapped[int] = mapped_column(

        Integer,

        nullable=False,

        default=0,

    )

    message: Mapped[str] = mapped_column(

        Text,

        nullable=False,

    )

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(UTC),

        nullable=False,

    )

    project = relationship("Project")

    build = relationship("Build")

    security_scan = relationship("SecurityScan")

    deployment = relationship("KubernetesDeployment")

