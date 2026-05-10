from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    org_id: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


# ─── Organization ───────────────────────────────
class OrgOut(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── API Key ────────────────────────────────────
class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class APIKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyOut):
    """Returned only on creation, includes the full key (never stored)."""
    raw_key: str
