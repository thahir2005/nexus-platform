from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KubernetesDeployment(Base):
    __tablename__ = "kubernetes_deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    environment_id: Mapped[int | None] = mapped_column(
        ForeignKey("environments.id"),
        nullable=True,
        index=True,
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

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    rollback_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("kubernetes_deployments.id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    project = relationship("Project")
    environment = relationship("Environment")
    rollback_of = relationship(
        "KubernetesDeployment",
        remote_side=[id],
    )