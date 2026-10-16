from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.build import Build
from app.models.project import Project
from app.models.security_scan import SecurityScan
from app.models.user import User

client = TestClient(app)


def _create_project(db, suffix):
    # Use the full unique suffix so two test users cannot share a username.
    user = User(
        username=f"scan-test-{suffix}",
        email=f"scan-test-{suffix}@example.invalid",
    )
    db.add(user)
    db.flush()

    project = Project(
        name=f"scan-project-{suffix}",
        owner_id=user.id,
    )
    db.add(project)
    db.flush()

    return project


def test_security_scan_rejects_nonexistent_project():
    with patch("app.api.security_scans.scan_image") as scan_image:
        response = client.post(
            "/api/v1/projects/2147483000/security-scan",
            params={"image_name": "example/test:latest"},
        )

    assert response.status_code == 404
    scan_image.assert_not_called()


def test_security_scan_rejects_build_from_another_project():
    db = SessionLocal()
    suffix = uuid4().hex
    project_ids = []
    user_ids = []

    try:
        owner_project = _create_project(db, f"{suffix}-owner")
        other_project = _create_project(db, f"{suffix}-other")

        owner_build = Build(
            project_id=owner_project.id,
            image_name="example/owner:latest",
            status="success",
            build_status="success",
            validation_status="valid",
        )
        db.add(owner_build)
        db.commit()

        project_ids = [owner_project.id, other_project.id]
        user_ids = [owner_project.owner_id, other_project.owner_id]
        other_project_id = other_project.id
        owner_build_id = owner_build.id

        with patch("app.api.security_scans.scan_image") as scan_image:
            response = client.post(
                f"/api/v1/projects/{other_project_id}/security-scan",
                params={
                    "image_name": "example/other:latest",
                    "build_id": owner_build_id,
                },
            )

        assert response.status_code == 404
        scan_image.assert_not_called()

    finally:
        db.rollback()
        db.close()

        # Clean up in foreign-key-safe order.
        if project_ids:
            cleanup_db = SessionLocal()
            try:
                cleanup_db.query(SecurityScan).filter(
                    SecurityScan.project_id.in_(project_ids)
                ).delete(synchronize_session=False)

                cleanup_db.query(Build).filter(
                    Build.project_id.in_(project_ids)
                ).delete(synchronize_session=False)

                cleanup_db.query(Project).filter(
                    Project.id.in_(project_ids)
                ).delete(synchronize_session=False)

                if user_ids:
                    cleanup_db.query(User).filter(
                        User.id.in_(user_ids)
                    ).delete(synchronize_session=False)

                cleanup_db.commit()
            finally:
                cleanup_db.close()

def test_security_scan_requires_authentication():
    from app.core.auth import get_current_user, require_request_access

    saved = {}
    for dependency in (get_current_user, require_request_access):
        saved[dependency] = app.dependency_overrides.pop(dependency, None)

    try:
        with patch("app.api.security_scans.scan_image") as scan_image:
            response = client.post(
                "/api/v1/projects/2147483000/security-scan",
                params={"image_name": "example/test:latest"},
            )

        assert response.status_code == 401
        scan_image.assert_not_called()
    finally:
        for dependency, override in saved.items():
            if override is not None:
                app.dependency_overrides[dependency] = override


def test_user_cannot_scan_another_users_project():
    from app.core.auth import get_current_user, require_request_access

    db = SessionLocal()
    suffix = uuid4().hex
    project_ids = []
    user_ids = []
    saved = {}

    try:
        foreign_project = _create_project(db, f"{suffix}-foreign")
        db.commit()
        project_id = foreign_project.id
        owner_id = foreign_project.owner_id
        project_ids.append(project_id)
        user_ids.append(owner_id)

        current_user = db.query(User).filter(
            User.email == "nexus-test-auth@example.invalid"
        ).first()
        assert current_user is not None
        current_user_id = current_user.id
    finally:
        db.close()

    for dependency in (get_current_user, require_request_access):
        saved[dependency] = app.dependency_overrides.pop(dependency, None)

    try:
        from app.core.auth import get_current_user

        def current_test_user():
            lookup_db = SessionLocal()
            try:
                user = lookup_db.get(User, current_user_id)
                assert user is not None
                return User(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    clerk_user_id=user.clerk_user_id,
                )
            finally:
                lookup_db.close()

        app.dependency_overrides[get_current_user] = current_test_user

        with patch("app.api.security_scans.scan_image") as scan_image:
            response = client.post(
                f"/api/v1/projects/{project_id}/security-scan",
                params={"image_name": "example/foreign:latest"},
            )

        assert response.status_code == 404
        scan_image.assert_not_called()
    finally:
        for dependency, override in saved.items():
            if override is not None:
                app.dependency_overrides[dependency] = override

        cleanup_db = SessionLocal()
        try:
            cleanup_db.query(SecurityScan).filter(
                SecurityScan.project_id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(Build).filter(
                Build.project_id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(Project).filter(
                Project.id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(User).filter(
                User.id.in_(user_ids)
            ).delete(synchronize_session=False)
            cleanup_db.commit()
        finally:
            cleanup_db.close()


def test_user_cannot_read_another_users_security_scan_history():
    from app.core.auth import get_current_user, require_request_access

    db = SessionLocal()
    suffix = uuid4().hex
    project_ids = []
    user_ids = []
    saved = {}

    try:
        foreign_project = _create_project(db, f"{suffix}-history")
        db.commit()
        project_id = foreign_project.id
        owner_id = foreign_project.owner_id
        project_ids.append(project_id)
        user_ids.append(owner_id)

        current_user = db.query(User).filter(
            User.email == "nexus-test-auth@example.invalid"
        ).first()
        assert current_user is not None
        current_user_id = current_user.id
    finally:
        db.close()

    for dependency in (get_current_user, require_request_access):
        saved[dependency] = app.dependency_overrides.pop(dependency, None)

    try:
        def current_test_user():
            lookup_db = SessionLocal()
            try:
                user = lookup_db.get(User, current_user_id)
                assert user is not None
                return User(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    clerk_user_id=user.clerk_user_id,
                )
            finally:
                lookup_db.close()

        app.dependency_overrides[get_current_user] = current_test_user

        response = client.get(
            f"/api/v1/projects/{project_id}/security-scans"
        )

        assert response.status_code == 404
    finally:
        for dependency, override in saved.items():
            if override is not None:
                app.dependency_overrides[dependency] = override

        cleanup_db = SessionLocal()
        try:
            cleanup_db.query(SecurityScan).filter(
                SecurityScan.project_id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(Build).filter(
                Build.project_id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(Project).filter(
                Project.id.in_(project_ids)
            ).delete(synchronize_session=False)
            cleanup_db.query(User).filter(
                User.id.in_(user_ids)
            ).delete(synchronize_session=False)
            cleanup_db.commit()
        finally:
            cleanup_db.close()
