"""Authentication & API key management routes.

Endpoints:
  POST /signup         Register + create org (returns access token + refresh cookie)
  POST /login          Login with credentials (returns access token + refresh cookie)
  POST /refresh        Refresh via HTTP-only cookie
  POST /logout         Clear refresh cookie
  GET  /me             Current user profile
  POST /invite         Invite user to org (admin+)
  POST /api-keys       Generate API key (admin+)
  GET  /api-keys       List API keys (admin+)
  DELETE /api-keys/{id} Revoke API key (admin+)
"""

from fastapi import APIRouter, Depends, Request, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_current_user, require_admin
from app.core.exceptions import AuthenticationError, NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    SignupRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserOut, APIKeyCreate, APIKeyOut, APIKeyCreated, InviteRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)

# Cookie config
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _set_refresh_cookie(response: Response, refresh_token: str):
    """Set the refresh token as an HTTP-only, secure cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,       # Not accessible via JavaScript
        secure=False,        # Set True in production (HTTPS only)
        samesite="lax",      # CSRF protection
        path="/api/v1/auth", # Only sent to auth endpoints
    )


def _clear_refresh_cookie(response: Response):
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        secure=False,
        samesite="lax",
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signup(request: Request, response: Response, data: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their organization.

    Returns access_token in body, refresh_token as HTTP-only cookie.
    """
    result = await AuthService.signup(db, data)
    _set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(request: Request, response: Response, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password.

    Returns access_token in body, refresh_token as HTTP-only cookie.
    """
    result = await AuthService.login(db, data)
    _set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token.

    Accepts refresh token from:
      1. HTTP-only cookie (preferred, automatic)
      2. Request body (fallback for mobile/non-browser clients)
    """
    # Try cookie first, then body
    token = refresh_token or (data.refresh_token if data else None)
    if not token:
        raise AuthenticationError("No refresh token provided (check cookie or body)")

    result = await AuthService.refresh(db, token)
    _set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Logout by clearing the refresh token cookie."""
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return UserOut.model_validate(current_user)


# ─── Invite ──────────────────────────────────────
@router.post("/invite", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: InviteRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new user to the current organization."""
    user = await AuthService.invite_user(db, current_user.org_id, data.email, data.role)
    return UserOut.model_validate(user)


# ─── API Keys ────────────────────────────────────
@router.post("/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for data ingestion."""
    return await AuthService.create_api_key(db, current_user, data.name)


@router.get("/api-keys", response_model=list[APIKeyOut])
async def list_api_keys(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all active API keys for the organization."""
    keys = await AuthService.list_api_keys(db, current_user.org_id)
    return [APIKeyOut.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    success = await AuthService.revoke_api_key(db, key_id, current_user.org_id)
    if not success:
        raise NotFoundError(resource="APIKey", resource_id=key_id)


@router.post("/api-keys/{key_id}/rotate", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def rotate_api_key(
    key_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Rotate an API key — revokes the old one and issues a new key with the same name."""
    result = await AuthService.rotate_api_key(db, key_id, current_user)
    if not result:
        raise NotFoundError(resource="APIKey", resource_id=key_id)
    return result


# ─── Google OAuth2 ────────────────────────────────
from urllib.parse import urlencode
from app.core.config import settings
import httpx as _httpx

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login():
    """Redirect to Google OAuth2 consent screen.

    Frontend should open this URL or redirect the user here.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise AuthenticationError("Google OAuth is not configured (set GOOGLE_CLIENT_ID)")

    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    })
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{params}"}


@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback.

    Exchanges authorization code for tokens, fetches user info,
    and creates/logs-in the user.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise AuthenticationError("Google OAuth is not configured")

    # Exchange code for tokens
    async with _httpx.AsyncClient() as http:
        token_resp = await http.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_resp.status_code != 200:
            raise AuthenticationError("Failed to exchange Google auth code")
        tokens = token_resp.json()

        # Fetch user info
        userinfo_resp = await http.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        })
        if userinfo_resp.status_code != 200:
            raise AuthenticationError("Failed to fetch Google user info")
        userinfo = userinfo_resp.json()

    email = userinfo.get("email")
    name = userinfo.get("name", email.split("@")[0])

    if not email:
        raise AuthenticationError("Google account has no email")

    result = await AuthService.google_signin(db, email, name)
    _set_refresh_cookie(response, result.refresh_token)

    # Redirect to frontend with access token
    from urllib.parse import quote
    redirect_url = f"{settings.FRONTEND_URL}/login?token={quote(result.access_token)}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url, status_code=302)
