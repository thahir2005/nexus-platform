"""Test-only authenticated-user overrides for legacy API integration tests.

These overrides are scoped to pytest and never loaded by the production app.
Security-specific tests explicitly remove them to verify unauthenticated access.
"""
from collections.abc import Generator

import pytest
from sqlalchemy import select

from app.core.auth import get_current_user, require_request_access
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def authenticated_api_test_user() -> Generator[User, None, None]:
    db = SessionLocal()
    try:
        user = db.scalar(
            select(User).where(User.email == "nexus-test-auth@example.invalid")
        )
        if user is None:
            user = User(
                username="nexus-test-auth",
                email="nexus-test-auth@example.invalid",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        # Copy scalar fields to a detached instance before closing this session.
        test_user = User(
            id=user.id,
            username=user.username,
            email=user.email,
            clerk_user_id=user.clerk_user_id,
        )
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_request_access] = lambda: test_user
    try:
        yield test_user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_request_access, None)
