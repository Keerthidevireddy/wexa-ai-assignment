import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.models.user import User, Organization, APIKey, UserRole
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserOut, APIKeyCreated


class AuthService:

    @staticmethod
    async def signup(db: AsyncSession, data: SignupRequest) -> TokenResponse:
        # Check if user exists
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(message="Email already registered", details={"email": data.email})

        # Create org
        slug = data.org_name.lower().replace(" ", "-")[:50] + "-" + str(uuid.uuid4())[:8]
        org = Organization(name=data.org_name, slug=slug)
        db.add(org)
        await db.flush()

        # Create user
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.OWNER,
            org_id=org.id,
        )
        db.add(user)
        await db.flush()

        access_token = create_access_token(user.id, {"org_id": org.id, "role": user.role})
        refresh_token = create_refresh_token(user.id)
        user_out = UserOut.model_validate(user)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_out)

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account disabled")

        access_token = create_access_token(user.id, {"org_id": user.org_id, "role": user.role})
        refresh_token = create_refresh_token(user.id)
        user_out = UserOut.model_validate(user)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_out)

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user_id = payload["sub"]
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError(resource="User", resource_id=user_id)

        access_token = create_access_token(user.id, {"org_id": user.org_id, "role": user.role})
        new_refresh = create_refresh_token(user.id)
        user_out = UserOut.model_validate(user)

        return TokenResponse(access_token=access_token, refresh_token=new_refresh, user=user_out)

    @staticmethod
    async def create_api_key(db: AsyncSession, user: User, name: str) -> APIKeyCreated:
        raw_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hash_password(raw_key)
        key_prefix = raw_key[:12]

        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            org_id=user.org_id,
            created_by=user.id,
        )
        db.add(api_key)
        await db.flush()

        out = APIKeyCreated(
            id=api_key.id,
            name=api_key.name,
            key_prefix=key_prefix,
            is_active=True,
            created_at=api_key.created_at,
            last_used_at=None,
            raw_key=raw_key,
        )
        return out

    @staticmethod
    async def list_api_keys(db: AsyncSession, org_id: str):
        result = await db.execute(select(APIKey).where(APIKey.org_id == org_id, APIKey.is_active == True))
        return result.scalars().all()

    @staticmethod
    async def revoke_api_key(db: AsyncSession, key_id: str, org_id: str) -> bool:
        result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.org_id == org_id))
        key = result.scalar_one_or_none()
        if not key:
            return False
        key.is_active = False
        return True

    @staticmethod
    async def rotate_api_key(db: AsyncSession, key_id: str, user: "User") -> APIKeyCreated | None:
        """Rotate an API key: revoke old, create new with same name."""
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.org_id == user.org_id)
        )
        old_key = result.scalar_one_or_none()
        if not old_key:
            return None

        # Revoke old
        old_key.is_active = False
        old_name = old_key.name

        # Create new with same name
        return await AuthService.create_api_key(db, user, old_name)

    @staticmethod
    async def invite_user(db: AsyncSession, org_id: str, email: str, role: str) -> User:
        """Invite a new user to the organization."""
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError(message="User already exists", details={"email": email})

        # Create user with temp password (they should reset)
        temp_password = secrets.token_urlsafe(16)
        user = User(
            email=email,
            hashed_password=hash_password(temp_password),
            role=UserRole(role) if role in [r.value for r in UserRole] else UserRole.VIEWER,
            org_id=org_id,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def google_signin(db: AsyncSession, google_email: str, google_name: str) -> TokenResponse:
        """Handle Google OAuth2 sign-in: create account if new, login if exists."""
        result = await db.execute(select(User).where(User.email == google_email))
        user = result.scalar_one_or_none()

        if user:
            # Existing user — just log them in
            if not user.is_active:
                raise AuthenticationError("Account disabled")
        else:
            # New user — create org + user
            slug = google_name.lower().replace(" ", "-")[:30] + "-" + str(uuid.uuid4())[:8]
            org = Organization(name=f"{google_name}'s Org", slug=slug)
            db.add(org)
            await db.flush()

            user = User(
                email=google_email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),  # random, unused
                full_name=google_name,
                role=UserRole.OWNER,
                org_id=org.id,
            )
            db.add(user)
            await db.flush()

        access_token = create_access_token(user.id, {"org_id": user.org_id, "role": user.role})
        refresh_token = create_refresh_token(user.id)
        user_out = UserOut.model_validate(user)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_out)

