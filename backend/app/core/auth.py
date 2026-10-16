"""Clerk session verification and per-project authorization."""
from functools import lru_cache

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.models.environment import Environment
from app.models.project import Project
from app.models.user import User


@lru_cache(maxsize=1)
def _clerk_client(secret_key: str) -> Clerk:
    return Clerk(bearer_auth=secret_key)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid authentication is required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _field(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _provision_user(clerk_user_id: str, db: Session) -> User:
    """Provision a local account from the verified Clerk profile only."""
    secret_key = settings.clerk_secret_key
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not provisioned; Clerk profile lookup is unavailable",
        )
    try:
        profile = _clerk_client(secret_key).users.get(user_id=clerk_user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify account profile with identity provider",
        ) from None

    email_addresses = _field(profile, "email_addresses", []) or []
    primary_id = _field(profile, "primary_email_address_id")
    verified_email = None
    for address in email_addresses:
        address_id = _field(address, "id")
        verification = _field(address, "verification")
        verification_status = _field(verification, "status")
        if address_id == primary_id and verification_status == "verified":
            verified_email = _field(address, "email_address")
            break
    if not verified_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified primary email is required to use NEXUS",
        )

    user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user:
        return user

    # Linking by email is permitted only because the email came from the
    # verified primary address returned by Clerk's server-side API.
    user = db.scalar(select(User).where(User.email == verified_email))
    if user:
        if user.clerk_user_id and user.clerk_user_id != clerk_user_id:
            raise HTTPException(status_code=409, detail="Email is linked to another account")
        user.clerk_user_id = clerk_user_id
        db.commit()
        db.refresh(user)
        return user

    username = _field(profile, "username") or verified_email.split("@", 1)[0]
    username = str(username)[:80] or "nexus-user"
    if db.scalar(select(User.id).where(User.username == username)):
        username = f"{username[:65]}-{clerk_user_id[-12:]}"

    user = User(username=username, email=verified_email, clerk_user_id=clerk_user_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Handle a simultaneous first login without creating duplicate accounts.
        user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
        if user:
            return user
        raise HTTPException(status_code=409, detail="Account provisioning conflict") from None
    db.refresh(user)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    secret_key = settings.clerk_secret_key
    jwt_key = settings.clerk_jwt_key
    if not secret_key and not jwt_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    options = AuthenticateRequestOptions(
        secret_key=secret_key,
        jwt_key=jwt_key,
        authorized_parties=[
            item.strip()
            for item in settings.clerk_authorized_parties.split(",")
            if item.strip()
        ],
        accepts_token=["session_token"],
    )
    try:
        client = _clerk_client(secret_key) if secret_key else Clerk()
        state = client.authenticate_request(request, options)
    except Exception:
        raise _unauthorized() from None

    if not state.is_authenticated or not state.payload:
        raise _unauthorized()
    clerk_user_id = state.payload.get("sub")
    if not isinstance(clerk_user_id, str) or not clerk_user_id:
        raise _unauthorized()

    user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user is None:
        user = _provision_user(clerk_user_id, db)
    return user


async def require_request_access(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Require a valid session and enforce ownership for project-scoped routes."""
    params = request.path_params
    project_id = params.get("project_id")
    environment_id = params.get("environment_id")

    # Several legacy POST endpoints put project_id in JSON instead of the URL.
    if project_id is None and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            body = await request.json()
            if isinstance(body, dict):
                project_id = body.get("project_id")
        except Exception:
            pass

    project = None
    if project_id is not None:
        try:
            project = db.get(Project, int(project_id))
        except (TypeError, ValueError):
            project = None
        if project is None or project.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Project not found")

    if project is None and environment_id is not None:
        try:
            environment = db.get(Environment, int(environment_id))
        except (TypeError, ValueError):
            environment = None
        if environment is None:
            raise HTTPException(status_code=404, detail="Environment not found")
        project = db.get(Project, environment.project_id)
        if project is None or project.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Environment not found")

    return user
