"""
Purpose: Pydantic schemas for authentication workflows (login, registration,
token response, user serialization, password reset).  Kept concise (<150 LOC)
as specified in Phase 2 plan.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, validator


# --------------------------------------------------------------------------- #
#                                 INPUT MODELS                                #
# --------------------------------------------------------------------------- #


class UserLogin(BaseModel):
    """
    User login payload. Accepts either username or email to simplify UX.
    """

    username_or_email: str = Field(
        ...,
        min_length=3,
        max_length=100,
        examples=["alice", "alice@example.com"],
    )
    password: str = Field(..., min_length=8, max_length=128)

    @validator("username_or_email", pre=True)
    def strip_whitespace(cls, v: str) -> str:  # noqa: N805
        return v.strip().lower()

    class Config:
        json_schema_extra = {
            "example": {"username_or_email": "alice", "password": "hunter2"}
        }


class UserRegister(BaseModel):
    """
    Registration payload, optionally requires invite_code if enabled in settings.
    """

    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    invite_code: str | None = Field(
        None,
        description="Invite code required if registration is invite-only",
        examples=["INVITECODE"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "alice",
                "email": "alice@example.com",
                "password": "hunter2",
                "invite_code": "INVITECODE"
            }
        }


class PasswordResetRequest(BaseModel):
    """
    Step 1: user requests password reset.
    """

    email: EmailStr


class PasswordResetSubmit(BaseModel):
    """
    Step 2: user submits new password with token they received.
    """

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# --------------------------------------------------------------------------- #
#                                 OUTPUT MODELS                               #
# --------------------------------------------------------------------------- #


class TokenResponse(BaseModel):
    """
    Response returned on successful authentication.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration

    @classmethod
    def from_ttl(cls, token: str, ttl_minutes: int) -> "TokenResponse":
        return cls(access_token=token, expires_in=ttl_minutes * 60)


class UserResponse(BaseModel):
    """
    Public user information returned by /me endpoint.
    """

    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------- #
#                              MUTATION MODELS                               #
# --------------------------------------------------------------------------- #


class UserUpdate(BaseModel):
    """Partial update payload for the authenticated user's profile."""

    username: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        description="New username (must be unique)",
        examples=["alice"],
    )
    email: EmailStr | None = Field(
        None, description="New email address (must be unique)", examples=["alice@example.com"]
    )
    password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Optional new password (will be hashed server-side)",
    )

    @validator("username", "email", pre=True)
    def _strip_and_lower(cls, v: str | None):  # noqa: N805
        if v is None:
            return v
        return v.strip().lower()

    @validator("password", pre=True)
    def _strip(cls, v: str | None):  # noqa: N805
        if v is None:
            return v
        return v.strip()

    @validator("password")
    def _password_strength(cls, v: str | None):  # noqa: N805
        # Extra guard – length already enforced by Field but keep for clarity
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @classmethod
    def ensure_non_empty(cls, values):  # noqa: D401
        if not any(values.get(f) is not None for f in ("username", "email", "password")):
            raise ValueError("At least one field must be provided")
        return values

    class Config:  # noqa: D401
        json_schema_extra = {
            "example": {
                "username": "newalice",
                "email": "alice@newdomain.com",
                "password": "newpassword123",
            }
        }

    # Ensure at least one field present – works on Pydantic v1 & v2
    def __init__(self, **data):  # noqa: D401
        super().__init__(**data)
        if not any(
            getattr(self, field) is not None for field in ("username", "email", "password")
        ):
            raise ValueError("At least one field must be provided")


# --------------------------------------------------------------------------- #
#                               HELPER ALIASES                                #
# --------------------------------------------------------------------------- #

LoginSchema = UserLogin
RegisterSchema = UserRegister

# Ensure all forward references for this model are resolved for FastAPI+Pydantic
UserRegister.model_rebuild()
globals()["UserRegister"] = UserRegister
