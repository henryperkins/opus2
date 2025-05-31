"""
Purpose: Pydantic schemas for authentication workflows (login, registration,
token response, user serialization, password reset).  Kept concise (<150 LOC)
as specified in Phase 2 plan.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

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
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {"username_or_email": "alice", "password": "hunter2"}
        }


class UserRegister(BaseModel):
    """
    Registration payload (invite-only flow).
    """

    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    invite_code: str = Field(..., examples=["code1"])

    class Config:
        json_schema_extra = {
            "example": {
                "username": "alice",
                "email": "alice@example.com",
                "password": "hunter2",
                "invite_code": "code1",
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
        orm_mode = True


# --------------------------------------------------------------------------- #
#                               HELPER ALIASES                                #
# --------------------------------------------------------------------------- #

LoginSchema = UserLogin
RegisterSchema = UserRegister
