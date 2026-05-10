"""FastAPI dependency injection for authentication and authorization."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from JWT bearer token."""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise AuthenticationError("Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Malformed token: missing subject")

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found or deactivated")

    return user


def require_roles(*roles: UserRole):
    """Factory for role-based authorization guards."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in [r.value if isinstance(r, UserRole) else r for r in roles]:
            raise AuthorizationError(
                message=f"Requires one of roles: {[r.value for r in roles]}",
                details={"current_role": current_user.role, "required": [r.value for r in roles]},
            )
        return current_user

    return checker


# Pre-built role guards
require_owner = require_roles(UserRole.OWNER)
require_admin = require_roles(UserRole.OWNER, UserRole.ADMIN)
require_analyst = require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.ANALYST)
