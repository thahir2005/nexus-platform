from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SecurityScan(Base):
    __tablename__ = "security_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    build_id: Mapped[int | None] = mapped_column(
        ForeignKey("builds.id"),
        nullable=True,
        index=True,
    )

    image_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    unknown_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    low_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    medium_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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

    findings: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    project = relationship("Project")
    build = relationship("Build")