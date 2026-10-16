from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import SessionLocal
from app.models.build import Build
from app.models.project import Project
from app.models.security_scan import SecurityScan
from app.models.user import User
from app.schemas.security_scan import SecurityScanResponse
from app.services.trivy_scanner import scan_image

router = APIRouter(
    prefix="/api/v1",
    tags=["security"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_owned_project(
    project_id: int,
    user: User,
    db: Session,
) -> Project:
    """Return a project only when it belongs to the authenticated user."""
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == user.id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


@router.post(
    "/projects/{project_id}/security-scan",
    response_model=SecurityScanResponse,
)
def run_security_scan(
    project_id: int,
    image_name: str,
    build_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_project(project_id, user, db)

    if build_id is not None:
        build = (
            db.query(Build)
            .filter(
                Build.id == build_id,
                Build.project_id == project_id,
            )
            .first()
        )

        if build is None:
            raise HTTPException(
                status_code=404,
                detail="Build not found",
            )

    result = scan_image(image_name)

    scan = SecurityScan(
        project_id=project_id,
        build_id=build_id,
        image_name=image_name,
        status=result.status,
        unknown_count=result.unknown_count,
        low_count=result.low_count,
        medium_count=result.medium_count,
        high_count=result.high_count,
        critical_count=result.critical_count,
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    return scan


@router.get(
    "/projects/{project_id}/security-scans",
    response_model=list[SecurityScanResponse],
)
def get_security_scan_history(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_project(project_id, user, db)

    return (
        db.query(SecurityScan)
        .filter(SecurityScan.project_id == project_id)
        .order_by(SecurityScan.created_at.desc())
        .all()
    )


@router.get(
    "/projects/{project_id}/security-scans/{scan_id}",
    response_model=SecurityScanResponse,
)
def get_security_scan(
    project_id: int,
    scan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_project(project_id, user, db)

    scan = (
        db.query(SecurityScan)
        .filter(
            SecurityScan.id == scan_id,
            SecurityScan.project_id == project_id,
        )
        .first()
    )

    if scan is None:
        raise HTTPException(
            status_code=404,
            detail="Security scan not found",
        )

    return scan