from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.security_scan import SecurityScan
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


@router.post(
    "/projects/{project_id}/security-scan",
    response_model=SecurityScanResponse,
)
def run_security_scan(
    project_id: int,
    image_name: str,
    build_id: int | None = None,
    db: Session = Depends(get_db),
):
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