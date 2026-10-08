from unittest.mock import patch

from app.db.session import SessionLocal
from app.models.security_scan import SecurityScan
from app.services.build_pipeline import run_build_pipeline


def test_pipeline_blocks_when_security_scan_fails():
    db = SessionLocal()

    result = None

    try:
        with (
            patch("app.services.build_pipeline.build_image") as mock_build,
            patch("app.services.build_pipeline.validate_image") as mock_validate,
            patch("app.services.build_pipeline.scan_image") as mock_scan,
        ):
            mock_build.return_value.status = "success"

            mock_validate.return_value.status = "valid"
            mock_validate.return_value.architecture = "arm64"
            mock_validate.return_value.os = "linux"

            mock_scan.return_value.status = "blocked"
            mock_scan.return_value.unknown_count = 0
            mock_scan.return_value.low_count = 0
            mock_scan.return_value.medium_count = 2
            mock_scan.return_value.high_count = 3
            mock_scan.return_value.critical_count = 1
            mock_scan.return_value.message = (
                "Security gate blocked: HIGH or CRITICAL vulnerabilities detected"
            )

            mock_scan.return_value.findings = []

            result = run_build_pipeline(
                db=db,
                project_id=1,
                repository_path="/tmp/test-repository",
                image_name="nexus/test-image",
            )

        assert result.status == "failed"
        assert result.build_status == "success"
        assert result.validation_status == "valid"
        assert result.security_status == "blocked"
        assert result.high_count == 3
        assert result.critical_count == 1
        assert result.security_scan_id is not None

    finally:
        if result is not None and result.security_scan_id is not None:
            scan = db.get(SecurityScan, result.security_scan_id)
            if scan:
                db.delete(scan)

        db.commit()
        db.close()