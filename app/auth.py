"""Mock token authentication and role helpers."""

from fastapi import Header

from app.errors import AuthRequired, InvalidToken
from app.mock_data import USERS_BY_TOKEN


def get_current_user(authorization: str | None = Header(default=None, description="Bearer token, e.g. 'Bearer user-a-token'")) -> dict:
    """FastAPI dependency: returns the user for the Bearer token or raises 401."""
    if not authorization or not authorization.strip():
        raise AuthRequired()

    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthRequired("The Authorization header must use the format 'Bearer <token>'.")

    user = USERS_BY_TOKEN.get(token.strip())
    if user is None:
        raise InvalidToken()
    return user


def is_admin(user: dict) -> bool:
    return user["role"] == "admin"


def can_access(user: dict, task: dict) -> bool:
    """Admins can access every task; regular users only their own."""
    return is_admin(user) or task["ownerId"] == user["id"]